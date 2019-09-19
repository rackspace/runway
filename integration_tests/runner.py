"""Runner for integration tests."""
from __future__ import print_function
import os
import logging
from integration_test import IntegrationTest
from util import (execute_tests, import_tests)


class Runner(object):
    """Runner for all integration tests."""

    # Set working directory and logger
    WORKING_DIR = os.path.abspath(os.path.dirname(__file__))
    LOGGER = logging.getLogger('testsuite')

    def __init__(self):
        """Initialize object."""
        if os.environ.get('DEBUG'):
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('testsuite')
        self.working_dir = os.path.abspath(os.path.dirname(__file__))

    def run_tests(self):
        """Run all integration test."""
        return execute_tests([test(self.logger) for test in IntegrationTest.__subclasses__()], self.logger)

    def main(self):
        """Main entry."""
        import_tests(self.logger, self.working_dir)
        errs = self.run_tests()
        if errs > 0:
            self.logger.error('Tests failed; Check logs.')
        return 1 if errs > 0 else 0


if __name__ == "__main__":
    RUNNER = Runner()
    RUNNER.main()
