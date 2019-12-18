"""Runner for integration tests."""
from __future__ import print_function
import os
import logging

from .integration_test import IntegrationTest
from .util import (execute_tests, import_tests)


class Runner(object):
    """Runner for all integration tests."""

    def __init__(self, test_to_run=None, use_abs=False):
        """Initialize object.

        Args:
            test_to_run: Name of a test to run.
            package: Used as the anchor for relative imports

        """
        self._use_abs = use_abs
        self._tests_imported = False
        if os.environ.get('DEBUG'):
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('testsuite')
        self.working_dir = os.path.abspath(os.path.dirname(__file__))
        if test_to_run:
            self.test_to_run = 'test_{0}/test_{0}'.format(test_to_run)
        else:
            self.test_to_run = 'test_*/test_*'

    @property
    def available_tests(self):
        if not self._tests_imported:
            import_tests(self.logger, self.working_dir, self.test_to_run, self._use_abs)
            self._tests_imported = True
        return IntegrationTest.__subclasses__()

    def run_tests(self):
        """Run all integration tests."""
        return execute_tests([test(self.logger) for test in self.available_tests],
                             self.logger)

    def main(self):
        """Import and run tests."""
        errs = self.run_tests()
        if errs > 0:
            self.logger.error('Tests failed; Check logs.')
        return 1 if errs > 0 else 0
