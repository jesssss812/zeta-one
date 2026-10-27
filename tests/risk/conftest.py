import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--live-models", action="store_true", default=False,
        help="run tests that call real model APIs (needs ANTHROPIC_API_KEY; costs money)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live-models"):
        return
    skip = pytest.mark.skip(reason="calls a real model API; pass --live-models to run")
    for item in items:
        if "live_models" in item.keywords:
            item.add_marker(skip)


def pytest_configure(config):
    config.addinivalue_line("markers", "live_models: calls a real model API; runs only with --live-models")
