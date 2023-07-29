import asyncio
from typing import List

import pytest


# write the summary of xfailed tests at the end of the test session
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_terminal_summary(terminalreporter):
    yield

    xfailed: List[pytest.TestReport] = terminalreporter.stats.get("xfailed", [])
    if xfailed:
        terminalreporter.write_sep("=", "XFAIL summary info", cyan=True, bold=True)

    for rep in xfailed:
        if not rep.failed:
            reason = getattr(rep, "wasxfail", "")
            terminalreporter.write("XFAIL", yellow=True)
            terminalreporter.write(f" {rep.nodeid} - {reason}\n")

            rep.longrepr.toterminal(terminalreporter._tw)
            terminalreporter.line("")


# write the arguments of the test after the test name
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):  # pylint: disable=unused-argument
    yield

    terminalreporter = item.config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter is not None and hasattr(item, "callspec"):
        callspec = item.callspec
        if callspec:
            params = {f"{name}={value}" for name, value in callspec.params.items()}
            terminalreporter.write(f"\nArguments: {', '.join(params)}")


# cannot put in boilerplate because pytest is a mess
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop

    # clean any remaining task to avoid the warning about pending tasks
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        # print(f"Cancelling task {task}")
        task.cancel()

    loop.close()
