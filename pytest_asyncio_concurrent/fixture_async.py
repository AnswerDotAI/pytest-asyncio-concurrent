import copy
import inspect
import asyncio
import functools

from typing import Any, Dict, Optional, Sequence
import warnings

import pytest
from _pytest import fixtures
from _pytest import nodes

event_loop_key = pytest.StashKey[asyncio.AbstractEventLoop]()


@pytest.hookimpl(specname="pytest_fixture_setup", tryfirst=True)
def pytest_fixture_setup_wrap_async(
    fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest
) -> None:
    """Wraps the fixture function of an async fixture in a synchronous function."""
    event_loop = request.config.stash[event_loop_key]
    if inspect.isasyncgenfunction(fixturedef.func):
        _wrap_asyncgen_fixture(fixturedef, event_loop)
    elif inspect.iscoroutinefunction(fixturedef.func):
        _wrap_asyncfunc_fixture(fixturedef, event_loop)


def _wrap_asyncgen_fixture(fixturedef: pytest.FixtureDef, event_loop) -> None:
    fixtureFunc = fixturedef.func

    @functools.wraps(fixtureFunc)
    def _asyncgen_fixture_wrapper(**kwargs: Any):
        gen_obj = fixtureFunc(**kwargs)

        async def setup():
            res = await gen_obj.__anext__()  # type: ignore[union-attr]
            return res

        async def teardown() -> None:
            try:
                await gen_obj.__anext__()  # type: ignore[union-attr]
            except StopAsyncIteration:
                pass
            else:
                msg = "Async generator fixture didn't stop."
                msg += "Yield only once."
                raise ValueError(msg)

        result = event_loop.run_until_complete(setup())
        yield result
        event_loop.run_until_complete(teardown())

    fixturedef.func = _asyncgen_fixture_wrapper  # type: ignore[misc]


def _wrap_asyncfunc_fixture(fixturedef: pytest.FixtureDef, event_loop) -> None:
    fixtureFunc = fixturedef.func

    @functools.wraps(fixtureFunc)
    def _async_fixture_wrapper(**kwargs: Dict[str, Any]):
        async def setup():
            res = await fixtureFunc(**kwargs)
            return res

        return event_loop.run_until_complete(setup())

    fixturedef.func = _async_fixture_wrapper  # type: ignore[misc]


fixture_cache_key = pytest.StashKey[Dict[str, Optional[Sequence[pytest.FixtureDef[Any]]]]]()


@pytest.hookimpl(specname="pytest_sessionstart", trylast=True)
def pytest_sessionstart_cache_fixture(session: pytest.Session):
    event_loop = session.config.stash[event_loop_key] = asyncio.new_event_loop()
    session.config.add_cleanup(event_loop.close)
    # This function in general utilized some private properties.

    # This is to solve two problem:
    # 1. Funtion scoped fixture result value got shared in different tests in same group.
    # 2. And fixture teardown got registered under right test using it.

    # FixtureDef for each fixture is unique and held in FixtureManger and got injected into
    # pytest.Item when the Item is constructed, and FixtureDef class is also in charge of
    # holding finalizers and cache value.

    # Fixture value caching is highly coupled with pytest entire lifecycle, implementing a
    # thirdparty fixture cache manager will be hard.
    # The first problem can be solved by shallow copy the fixtureDef, to split the cache_value.
    # The finalizers are stored in a private list property in fixtureDef, which need to touch
    # private API anyway.

    # If the private API change, finalizer errors from this fixture but in different
    # tests in same group will be reported in one function.

    fixManager: fixtures.FixtureManager = session.config.pluginmanager.get_plugin(
        "funcmanage"
    )  # type: ignore
    getfixturedefs_original = fixManager.getfixturedefs

    @functools.wraps(getfixturedefs_original)
    def getfixturedefs_wrapper(
        argname: str,
        node: nodes.Node,
    ) -> Optional[Sequence[pytest.FixtureDef[Any]]]:
        if fixture_cache_key not in node.stash:
            node.stash[fixture_cache_key] = {}

        cache = node.stash[fixture_cache_key]
        if argname not in cache:
            fixtureDefs = getfixturedefs_original(argname, node)

            if fixtureDefs:
                fixtureDefs = tuple(_clone_function_fixture(fixDef) for fixDef in fixtureDefs)

            cache[argname] = fixtureDefs

        return cache[argname]

    fixManager.getfixturedefs = getfixturedefs_wrapper  # type: ignore


def _clone_function_fixture(fixtureDef: pytest.FixtureDef) -> pytest.FixtureDef:
    if fixtureDef.scope != "function":
        return fixtureDef

    new_fixdef = copy.copy(fixtureDef)
    if hasattr(fixtureDef, "_finalizers"):
        new_fixdef._finalizers = []  # type: ignore
    else:
        warnings.warn(
            f"""
            pytest {pytest.__version__} changed internal property which this plugin relies on.
            The teardown error in fixture {fixtureDef.argname} might be reported in wrong place.
            Please raise an issue.
            """
        )

    return new_fixdef
