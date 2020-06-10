"""Pytest configuration, fixtures, and plugins."""


def pytest_addoption(parser):
    """Add pytest CLI options."""
    parser.addoption('--integration', action='store_true', default=False,
                     help='include integration tests in regular testing')
    parser.addoption('--integration-only', action='store_true', default=False,
                     help='run only integration tests')
