import doctest
import warnings

import pytest

FLAKY = doctest.register_optionflag("FLAKY")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed and hasattr(item, "dtest"):
        # Check if the failing example was marked # doctest: +FLAKY
        exc = call.excinfo.value
        example = getattr(exc, "example", None)
        if example is not None and example.options.get(FLAKY):
            warnings.warn(
                f"Flaky doctest failed: {item.nodeid}\n{report.longreprtext}",
                stacklevel=1,
            )
            report.outcome = "skipped"
            report.wasxfail = "Flaky doctest (network-dependent)"
