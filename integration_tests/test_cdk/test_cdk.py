"""Tests for the CDK module."""
import os
import glob

from integration_test import IntegrationTest
from send2trash import send2trash
from util import (copy_file, copy_dir, import_tests, execute_tests)

class TestCDK(IntegrationTest):
    """Test CDK based module scenarios"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    fixtures_dir = os.path.join(base_dir, 'fixtures')
    multiple_stacks_dir = os.path.join(fixtures_dir, 'multiple-stacks-app.cdk')
    tests_dir = os.path.join(base_dir, 'tests')

    cdk_test_dir = os.path.join(base_dir, 'cdk_test')

    def copy_fixture(self, name='multiple-stacks-app.cdk'):
        """Copy fixture files for test"""
        copy_dir(
            os.path.join(self.fixtures_dir, name),
            os.path.join(self.cdk_test_dir, name)
        )

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(self.fixtures_dir, 'runway-{}.yml'.format(template))
        copy_file(template_file, os.path.join(self.cdk_test_dir, 'runway.yml'))

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in TestCDK.__subclasses__()]
        self.logger.debug('FOUND TESTS: %s', tests)
        self.set_environment('dev')
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0
        return err_count

    def clean(self):
        """Clean up CDK module directory."""
        file_types = ('*.yaml', '*.yml')
        templates = []
        for file_type in file_types:
            templates.extend(glob.glob(os.path.join(self.cdk_test_dir, file_type)))
        for template in templates:
            if os.path.isfile(template):
                self.logger.debug('send2trash: "%s"', template)
                send2trash(template)
        folders = ['multiple-stacks-app.cdk', 'decline-deploy-app.cdk']
        for folder in folders:
            folder_path = os.path.join(self.cdk_test_dir, folder)
            if os.path.isdir(folder_path):
                self.logger.debug('send2trash: "%s"', folder_path)
                send2trash(folder_path)

    def teardown(self):
        """Teardown resources create during init."""
        self.clean()
