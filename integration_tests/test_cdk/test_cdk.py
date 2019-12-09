"""Tests for the CDK module."""
import os

from integration_test import IntegrationTest
from util import (copy_file, copy_dir, import_tests, execute_tests)

class TestCDK(IntegrationTest):
    """Test"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    fixtures_dir = os.path.join(base_dir, 'fixtures')
    sample_app_dir = os.path.join(fixtures_dir, 'sampleapp.cdk')
    tests_dir = os.path.join(base_dir, 'tests')

    cdk_test_dir = os.path.join(base_dir, 'cdk_test')

    def copy_fixture(self):
        copy_dir(self.sample_app_dir, os.path.join(self.cdk_test_dir, 'sampleapp.cdk'))

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(self.fixtures_dir, 'runway-{}.yml'.format(template))
        copy_file(template_file, os.path.join(self.cdk_test_dir, 'runway.yml'))

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in TestCDK.__subclasses__()]
        self.logger.debug('FOUND TESTS: %s', tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.logger.debug('Nothing to do during test teardown')
