"""Integration tests for hooks."""
import os
from integration_tests.integration_test import IntegrationTest
from integration_tests.util import (copy_file, import_tests,
                                    execute_tests, run_command)


class Hooks(IntegrationTest):
    """Base class for hook tests."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    tests_dir = os.path.join(base_dir, 'tests')

    def run(self):
        """Run tests."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in Hooks.__subclasses__()]
        if not tests:
            raise Exception('No tests were found.')
        self.logger.debug('FOUND TESTS: %s', tests)
        self.set_environment('dev')
        self.set_env_var('CI', '1')
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown tests."""
        self.unset_env_var('CI')
