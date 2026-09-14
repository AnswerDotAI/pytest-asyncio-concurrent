import pytest

pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def pytester_plugins(pytester: pytest.Pytester, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.setenv("PYTEST_PLUGINS", "pytest_asyncio_concurrent.plugin")
    pytester.makeini("[pytest]")
