"""Testing remote Path Sources in deployments."""
import os
import glob

from send2trash import send2trash

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import copy_file, import_tests, execute_tests


class TestSources(IntegrationTest):
    """Test sources."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    fixtures_dir = os.path.join(base_dir, 'fixtures')
    tests_dir = os.path.join(base_dir, 'tests')

    sources_test_dir = os.path.join(base_dir, 'sources_test')

    def __init__(self, logger):
        """Initialize."""
        IntegrationTest.__init__(self, logger)

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(self.fixtures_dir, 'runway-{}.yml'.format(template))
        copy_file(template_file, os.path.join(self.sources_test_dir, 'runway.yml'))

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, 'test_*')
        tests = [test(self.logger) for test in TestSources.__subclasses__()]
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
                self.sources_test_dir,
                file_type
            )))
        for template in templates:
            if os.path.isfile(template):
                self.logger.debug('send2trash: "%s"', template)
                send2trash(template)
        folders = ['.runway_cache']
        for folder in folders:
            folder_path = os.path.join(self.sources_test_dir, folder)
            if os.path.isdir(folder_path):
                self.logger.debug('send2trash: "%s"', folder_path)
                send2trash(folder_path)

    def teardown(self):
        """Teardown resources create during init."""
        self.clean()
