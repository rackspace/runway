"""Tests for Helm."""
from __future__ import print_function
import os
from integration_test import IntegrationTest
from util import (copy_file, import_tests, execute_tests, run_command)

class Helm(IntegrationTest):
    """Base class for all Helm testing."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    tests_dir = os.path.join(base_dir, 'tests')

    def run(self):
        """Find all Helm tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in Helm.__subclasses__()]
        self.logger.debug('FOUND TESTS: %s', tests)
        self.set_environment('dev')
        return execute_tests(tests, self.logger)

    def teardown(self):
        """Teardown resources create during init."""
        print("teardown")
