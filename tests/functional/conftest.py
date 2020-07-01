"""Pytest configuration, fixtures, and plugins."""


def pytest_ignore_collect(path, config):  # pylint: disable=unused-argument
    """Determine if this directory should have its tests collected."""
    return not config.option.functional
