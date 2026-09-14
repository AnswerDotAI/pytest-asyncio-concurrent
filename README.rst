==============================
pytest-asyncio-concurrent-fork
==============================

This is a temporary pytest compatibility fork of `pytest-asyncio-concurrent <https://github.com/czl9707/pytest-asyncio-concurrent>`_. The intent is to return to upstream once the fixes land there.

The fork registers concurrent tests as active during fixture setup and execution, as required by pytest 9.1. Async fixtures and concurrent tests share one session-owned event loop rather than relying on an implicit current loop.

.. image:: https://img.shields.io/pypi/v/pytest-asyncio-concurrent-fork.svg
    :target: https://pypi.org/project/pytest-asyncio-concurrent-fork
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-asyncio-concurrent-fork.svg
    :target: https://pypi.org/project/pytest-asyncio-concurrent-fork
    :alt: Python versions

.. image:: https://github.com/AnswerDotAI/pytest-asyncio-concurrent/actions/workflows/main.yml/badge.svg
    :target: https://github.com/AnswerDotAI/pytest-asyncio-concurrent/actions/workflows/main.yml
    :alt: See Build Status on GitHub Actions


System/Integration tests can take a really long time. 

And ``pytest-asyncio-concurrent`` A pytest plugin aiming to solve this by running asynchronous tests in true parallel, enabling faster execution for high I/O or network-bound test suites. 

Unlike ``pytest-asyncio``, which runs async tests **sequentially**, ``pytest-asyncio-concurrent`` takes advantage of Python's asyncio capabilities to execute tests **concurrently** by specifying **async group**.

Note: This plugin would more or less `Break Test Isolation Principle` \(for none function scoped fixture\). Please make sure your tests is ok to run concurrently before you use this plugin.


Key Features
------------

* Giving the capability to run pytest async functions.
* Providing granular control over Concurrency -- See **Async Group** for details
  
  * Specifying Async Group to control tests that can run together. 
  * Limitation: Only test functions defined under same direct parent can be put into same group.

* ``asyncio_concurrent`` mark accept a ``timeout`` parameter, which would throw error when test reach the given time.
* Compatible with ``pytest-asyncio``.

Key Concept: Async Group
------------------------

The plugin control tests concurrency by putting them into different groups.

* Limitation: Each group can **only** contain tests under **same direct parent**. For example, class methods within same class, or functions within same file.
* Explicitly specify group by providing ``group`` parameter to ``asyncio_concurrent`` mark. 

    * All tests marked with same group name will be executed together.
    * All tests will be skipped if the ``Same Parent`` rule got violated.

* Use default grouping strategy. The plugin accept ``--default-group-strategy`` cli parameter, or ``default_group_strategy`` in ini or toml file. Possible value: ``self``, ``parent``.
    
    * **self**\(default\): Each test will be executed by itself if no group provided.
    * **parent**: Tests will grouped by their parent node. For example, all method within same class will be grouped together.

Installation
------------

Replace the upstream distribution with the fork; do not install both, since they provide the same Python package and pytest plugin::

    $ pip uninstall pytest-asyncio-concurrent
    $ pip install pytest-asyncio-concurrent-fork

The marker and plugin names are unchanged. With pytest 8.4 or later, projects can load only the plugins they use:

.. code-block:: toml

    [tool.pytest.ini_options]
    addopts = "--disable-plugin-autoload -p asyncio-concurrent"

Use plain ``@pytest.fixture`` for async fixtures owned by this plugin. If also using ``pytest-asyncio``, explicitly load ``-p asyncio`` and use its strict mode so it does not take ownership of concurrent tests.


How this work?
--------------

This plugin extend ``pytest_runtestloop`` hook to handle async tests seperately.

In the 'async loop', tests are grouped by the `group` provided in the mark. and executed one group at a time.

In each group, instead of sequentially calling ``setup``, ``call``, ``teardown`` for individual test, these hooks are called for all tests in the group in batch.

The fixture lifecycle within group is handled by this plugin instead of pytest core, to work around pytest sequential test execution assumption.


Usage
-----

Run test Sequentially

.. code-block:: python

    @pytest.mark.asyncio_concurrent
    async def async_test_A():
        res = await wait_for_something_async()
        assert result.is_valid()

    @pytest.mark.asyncio_concurrent
    async def async_test_B():
        res = await wait_for_something_async()
        assert result.is_valid()


Run tests Concurrently

.. code-block:: python

    # the test below will run by itself
    @pytest.mark.asyncio_concurrent
    async def test_by_itself():
        res = await wait_for_something_async()
        assert result.is_valid()

    # the two tests below will run concurrently
    @pytest.mark.asyncio_concurrent(group="my_group")
    async def test_groupA():
        res = await wait_for_something_async()
        assert result.is_valid()

    # this one will have a 10s timeout
    @pytest.mark.asyncio_concurrent(group="my_group", timeout=10)
    async def test_groupB():
        res = await wait_for_something_async()
        assert result.is_valid()


Parametrized Tests

.. code-block:: python

    # the parametrized tests below will run sequential
    @pytest.mark.asyncio_concurrent
    @pytest.parametrize("p", [0, 1, 2])
    async def test_parametrize_sequential(p):
        res = await wait_for_something_async()
        assert result.is_valid()

    # the parametrized tests below will run concurrently
    @pytest.mark.asyncio_concurrent(group="my_group")
    @pytest.parametrize("p", [0, 1, 2])
    async def test_parametrize_concurrent():
        res = await wait_for_something_async()
        assert result.is_valid()


Contributing
------------

Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the ``MIT`` license, "pytest-asyncio-concurrent" is free and open source software
