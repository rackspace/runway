"""Runner for integration tests."""
from __future__ import print_function
import os
import logging
import sys
from integration_test import IntegrationTest
from util import (execute_tests, import_tests)


class Runner(object):
    """Runner for all integration tests."""

    def __init__(self, test_to_run):
        """Initialize object."""
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

    def run_tests(self):
        """Run all integration tests."""
        return execute_tests([test(self.logger) for test in IntegrationTest.__subclasses__()],
                             self.logger)

    def main(self):
        """Import and run tests."""
        import_tests(self.logger, self.working_dir, self.test_to_run)
        errs = self.run_tests()
        if errs > 0:
            self.logger.error('Tests failed; Check logs.')
        return 1 if errs > 0 else 0


if __name__ == "__main__":
    TEST_NAME = None
    if len(sys.argv) > 1:
        TEST_NAME = sys.argv[1]
    RUNNER = Runner(TEST_NAME)
    sys.exit(RUNNER.main())
