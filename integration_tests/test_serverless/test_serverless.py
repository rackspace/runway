"""Tests for Serverless."""
from __future__ import print_function
import os
from runway.util import change_dir
from integration_test import IntegrationTest
from util import (import_tests, execute_tests, run_command)


class Serverless(IntegrationTest):
    """Base class for all Serverless testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    tests_dir = os.path.join(base_dir, 'tests')

    def run(self):
        """Find all Terraform tests and run them."""
        import_tests(self.logger, self.base_dir, 'serverless_test')
        serverless_test = Serverless.__subclasses__()[0]

        tests = []
        for template in os.listdir(self.templates_dir):
            if os.path.isdir(os.path.join(self.templates_dir, template)):
                self.logger.info('Found template "%s"', template)
                test = serverless_test(template, self.templates_dir, self.environment, self.logger)
                tests.append(test)
            else:
                self.logger.warning('"%s" is not a directory, skipping...', template)

        return execute_tests(tests, self.logger)

    def teardown(self):
        """Teardown resources create during init."""
        # all resources should have been torn down in ServerlessTest class
