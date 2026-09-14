from textwrap import dedent
import pytest


def test_async_function_fixture(pytester: pytest.Pytester):
    """Make sure that async function fixture is got wrapped up"""

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture(scope="function")
            async def async_fixture_function():
                await asyncio.sleep(0.1)
                return asyncio.get_running_loop()

            @pytest.mark.asyncio_concurrent
            async def test_fixture_async(async_fixture_function):
                assert async_fixture_function is asyncio.get_running_loop()
            """
        )
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_async_gen_fixture(pytester: pytest.Pytester):
    """Make sure that async generator fixture is got wrapped up"""

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture(scope="function")
            async def async_fixture_gen():
                await asyncio.sleep(0.1)
                yield asyncio.get_running_loop()

            @pytest.mark.asyncio_concurrent
            async def test_fixture_async(async_fixture_gen):
                assert async_fixture_gen is asyncio.get_running_loop()
            """
        )
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_async_function_fixture_sync(pytester: pytest.Pytester):
    """
    Make sure that async function fixture is got wrapped up
    and consumerable by synced function
    """

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture(scope="function")
            async def async_fixture_function():
                await asyncio.sleep(0.1)
                return 1

            def test_fixture_async(async_fixture_function):
                assert async_fixture_function == 1
            """
        )
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_async_gen_fixture_sync(pytester: pytest.Pytester):
    """
    Make sure that async generator fixture is got wrapped up
    and consumerable by synced function
    """

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture(scope="function")
            async def async_fixture_gen():
                await asyncio.sleep(0.1)
                yield 1

            def test_fixture_async(async_fixture_gen):
                assert async_fixture_gen == 1
            """
        )
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_async_gen_fixture_error(pytester: pytest.Pytester):
    """
    Make sure that async generator fixture is got wrapped up
    and do not allow multiple yield
    """

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture(scope="function")
            async def async_fixture_gen():
                await asyncio.sleep(0.1)
                yield 1
                yield 1

            def test_fixture_async(async_fixture_gen):
                assert async_fixture_gen == 1
            """
        )
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1, errors=1)
