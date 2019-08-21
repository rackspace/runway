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

    def run_tests(self):
        """Run all integration test."""
        tests = IntegrationTest.__subclasses__()
        return execute_tests(self, tests)

    def main(self):
        """Main entry."""
        if os.environ.get('DEBUG'):
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        import_tests(self, self.WORKING_DIR)
        errs = self.run_tests()
        if errs > 0:
            self.LOGGER.error('Tests failed; Check logs.')
        return 1 if errs > 0 else 0


if __name__ == "__main__":
    RUNNER = Runner()
    RUNNER.main()
