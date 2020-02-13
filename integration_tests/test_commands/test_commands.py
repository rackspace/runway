"""Tests for runway commands."""
import os

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import (import_tests, execute_tests)


class Commands(IntegrationTest):
    """Base class for all runway command testing testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    tests_dir = os.path.join(base_dir, 'tests')

    def run(self):
        """Find all tests and run them."""
        suffix = os.getenv('COMMAND_SUFFIX', '*')
        pattern = 'test_{0}'.format(suffix)
        self.set_env_var('AWS_DEFAULT_REGION', 'us-east-1')
        import_tests(self.logger, self.tests_dir, pattern)
        tests = [test(self.logger, self.environment)
                 for test in Commands.__subclasses__()]
        if not tests:
            raise Exception('No tests were found.')
        self.logger.debug('FOUND TESTS: %s', tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.logger.debug('Nothing to do during test teardown')
