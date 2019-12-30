"""Tests for runway commands."""
import os

from integration_test import IntegrationTest
from util import (import_tests, execute_tests)


class TestRunwayCommands(IntegrationTest):
    """Base class for all runway command testing testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    tests_dir = os.path.join(base_dir, 'tests')

    def run(self):
        """Find all tests and run them."""
        suffix = os.getenv('COMMAND_SUFFIX', '*')
        pattern = 'test_{0}'.format(suffix)
        import_tests(self.logger, self.tests_dir, pattern)
        tests = [test(self.logger) for test in TestRunwayCommands.__subclasses__()]
        self.logger.debug('FOUND TESTS: %s', tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.logger.debug('Nothing to do during test teardown')
