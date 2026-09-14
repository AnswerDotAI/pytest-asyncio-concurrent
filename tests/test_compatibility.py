from textwrap import dedent
import pytest


def test_compatibility_with_pytest_asyncio(pytester: pytest.Pytester):
    """Make sure tests failed is reported correctly"""

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio
            async def test_passing():
                pass

            @pytest.mark.asyncio_concurrent
            async def test_failed():
                pass
            """
        )
    )
    # overwrite the conftest
    pytester.makeini(
        """
        [pytest]
        asyncio_default_fixture_loop_scope=function
        addopts = -p no:sugar
        """
    )

    result = pytester.runpytest("-p", "asyncio")
    result.assert_outcomes(passed=2)
