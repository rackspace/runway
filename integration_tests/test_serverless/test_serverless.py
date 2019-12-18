"""Tests for Serverless."""
from __future__ import print_function
import os
from send2trash import send2trash

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import (import_tests, execute_tests)


class Serverless(IntegrationTest):
    """Base class for all Serverless testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    tests_dir = os.path.join(base_dir, 'tests')

    def clean(self):
        """Cleanup serverless folder."""
        # cleanup any leftover .serverless folder
        serverless_folder = os.path.join(self.templates_dir,
                                         self.template_name,
                                         '.serverless')
        if os.path.isdir(serverless_folder):
            self.logger.debug('send2trash: "%s"', serverless_folder)
            send2trash(serverless_folder)

    def run(self):
        """Find all Serverless tests and run them."""
        self.set_env_var('CI', '1')
        import_tests(self.logger, self.base_dir, 'serverless_test')
        serverless_test = Serverless.__subclasses__()[0]

        tests = []
        for template in os.listdir(self.templates_dir):
            if os.path.isdir(os.path.join(self.templates_dir, template)):
                self.logger.info('Found template "%s"', template)
                test = serverless_test(template,
                                       self.templates_dir,
                                       self.environment,
                                       self.logger)
                tests.append(test)
            else:
                self.logger.warning('"%s" is not a directory, skipping...', template)

        if not tests:
            raise Exception('No tests were found.')

        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.unset_env_var('CI')
        # all resources should have been torn down in ServerlessTest class
