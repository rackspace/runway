"""Testing that module type detection is handled appropriately."""
import os
import glob

from send2trash import send2trash

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import (copy_file, copy_dir, import_tests,
                                    execute_tests)


class RunwayModuleTypeDetection(IntegrationTest):
    """Test that module type detection is handled."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    fixtures_dir = os.path.join(base_dir, 'fixtures')
    tests_dir = os.path.join(base_dir, 'tests')

    mtd_test_dir = os.path.join(base_dir, 'runway_module_type_detection_test_dir')

    def copy_fixture(self, name='two-regions-app.cfn'):
        """Copy fixture files for test."""
        copy_dir(
            os.path.join(self.fixtures_dir, name),
            os.path.join(self.mtd_test_dir, name)
        )

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(self.fixtures_dir, 'runway-{}.yml'.format(template))
        copy_file(template_file, os.path.join(self.mtd_test_dir, 'runway.yml'))

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [
            test(self.logger) for test in RunwayModuleTypeDetection.__subclasses__()
        ]
        if not tests:
            raise Exception('No tests were found.')
        self.logger.debug('FOUND TESTS: %s', tests)
        self.set_environment('dev')
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0
        return err_count

    def clean(self):
        """Clean up fixture test directory."""
        file_types = ('*.yaml', '*.yml')
        templates = []
        for file_type in file_types:
            templates.extend(glob.glob(os.path.join(
                self.mtd_test_dir,
                file_type
            )))
        for template in templates:
            if os.path.isfile(template):
                self.logger.debug('send2trash: "%s"', template)
                send2trash(template)
        folders = ['']
        for folder in folders:
            folder_path = os.path.join(self.mtd_test_dir, folder)
            if os.path.isdir(folder_path):
                self.logger.debug('send2trash: "%s"', folder_path)
                send2trash(folder_path)

    def teardown(self):
        """Teardown resources create during init."""
        self.clean()
