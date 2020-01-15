"""Testing that the repository specified is downloaded to the correct directory."""

import os

from integration_tests.test_sources.test_sources import TestSources
from runway.util import change_dir
from util import run_command


class TestGitRemoteRepositoryCloned(TestSources):
    """Test deploying two regions in series."""

    TEST_NAME = __name__

    def __init__(self, logger):
        """Init class."""
        TestSources.__init__(self, logger)
        self.logger = logger

    def deploy(self):
        """Deploy provider."""
        self.copy_runway('git')
        with change_dir(self.sources_test_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_environment('dev')
        self.deploy()
        with change_dir(self.sources_test_dir):
            self.logger.info(os.path.isdir('.runway_cache'))
            assert os.path.isdir('.runway_cache')

        change_dir(self.base_dir)

    def teardown(self):
        """Teardown scaffolding."""
        self.set_env_var('CI', '1')
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.sources_test_dir):
            run_command(['runway', 'destroy'])
        self.clean()
        self.unset_env_var('CI')
