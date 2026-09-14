import copy
import sys
import dataclasses
from typing import Any, Callable, Dict, List

import pytest
from _pytest import fixtures
from _pytest import outcomes


if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup


class PytestAsyncioConcurrentGroupingWarning(pytest.PytestWarning):
    """Raised when Test from different parent grouped into same group."""


class PytestAsyncioConcurrentInvalidMarkWarning(pytest.PytestWarning):
    """Raised when Sync Test got marked."""


class PytestAysncioGroupInvokeError(BaseException):
    """Raised when AsyncioGroup got invoked"""


class AsyncioConcurrentGroup(pytest.Function):
    """
    The Function Group containing underneath children functions.
    AsyncioConcurrentGroup will be pushed onto `SetupState` representing all children.
    and in charging of holding and tearing down the finalizers from all children nodes.
    """

    children: List["AsyncioConcurrentGroupMember"]
    children_have_same_parent: bool
    children_finalizer: Dict["AsyncioConcurrentGroupMember", List[Callable[[], Any]]]
    has_setup: bool

    def __init__(
        self,
        parent,
        originalname: str,
    ):
        self.children_have_same_parent = True
        self.has_setup = False
        self.children = []
        self.children_finalizer = {}
        super().__init__(
            name=originalname,
            parent=parent,
            callobj=lambda: None,
        )

    def runtest(self) -> None:
        raise PytestAysncioGroupInvokeError()

    def setup(self) -> None:
        pass

    def add_child(self, item: "AsyncioConcurrentGroupMember") -> None:
        child_parent = list(item.iter_parents())[1]

        if child_parent is not self.parent:
            self.children_have_same_parent = False
            for child in self.children:
                child.add_marker("skip")

        if not self.children_have_same_parent:
            item.add_marker("skip")

        item.group = self
        self.children.append(item)
        self.children_finalizer[item] = []

    def teardown_child(self, item: "AsyncioConcurrentGroupMember") -> None:
        item.session._setupstate.stack.pop(item, None)
        finalizers = self.children_finalizer.pop(item)
        exceptions = []

        while finalizers:
            fin = finalizers.pop()
            try:
                fin()
            except outcomes.TEST_OUTCOME as e:
                exceptions.append(e)

        if len(exceptions) == 1:
            raise exceptions[0]
        elif len(exceptions) > 1:
            msg = f"errors while tearing down {item!r}"
            raise BaseExceptionGroup(msg, exceptions[::-1])

    def remove_child(self, item: "AsyncioConcurrentGroupMember") -> None:
        assert item in self.children
        self.children.remove(item)
        self.children_finalizer.pop(item)


class AsyncioConcurrentGroupMember(pytest.Function):
    """
    A light wrapper around Function, representing a child of AsyncioConcurrentGroup.
    The group registers active members in SetupState and tears them down individually.
    """

    group: AsyncioConcurrentGroup
    _inner: pytest.Function

    @staticmethod
    def promote_from_function(item: pytest.Function) -> "AsyncioConcurrentGroupMember":
        AsyncioConcurrentGroupMember._refresh_function_scoped_fixture(item)
        member = AsyncioConcurrentGroupMember.from_parent(
            name=item.name,
            parent=item.parent,
            callspec=item.callspec if hasattr(item, "callspec") else None,
            callobj=item.obj,
            keywords=item.keywords,
            fixtureinfo=item._fixtureinfo,
            originalname=item.originalname,
        )

        member._inner = item
        return member

    @staticmethod
    def _refresh_function_scoped_fixture(item: pytest.Function):
        # Parametrized tests will use their meta func to gather fixture information
        # on collection, which means they all share same fixture infomation.
        # Have to refresh fixtureDef here to get their own their own fixtureDef

        if not hasattr(item, "callspec"):
            return

        fixtureManager: fixtures.FixtureManager = item.config.pluginmanager.get_plugin(
            "funcmanage"
        )  # type: ignore

        new_name2fixturedefs = {}
        for name in item._fixtureinfo.name2fixturedefs.keys():
            if name in item.callspec.params.keys():
                new_name2fixturedefs[name] = item._fixtureinfo.name2fixturedefs[name]
            else:
                new_name2fixturedefs[name] = fixtureManager.getfixturedefs(
                    name, item
                )  # type: ignore

        try:
            item._fixtureinfo = dataclasses.replace(
                item._fixtureinfo, name2fixturedefs=new_name2fixturedefs
            )
        except TypeError:  # if item._fixtureinfo no longer a dataclass
            item._fixtureinfo = copy.copy(item._fixtureinfo)
            item._fixtureinfo.name2fixturedefs = new_name2fixturedefs  # type: ignore
