"""Test that two regions can be deployed in parallel."""

from test_parallelism.test_parallelism import TestParallelism
from runway.util import change_dir
from util import run_command


class TestTwoRegions(TestParallelism):
    """Test deploying two regions in parallel."""

    TEST_NAME = __name__

    def __init__(self, logger):
        """Init class."""
        TestParallelism.__init__(self, logger)
        self.logger = logger

    def deploy(self):
        """Deploy provider."""
        self.copy_runway('two-regions')
        self.copy_fixture('two-regions-app.sls')
        with change_dir(self.parallelism_test_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_environment('dev')
        self.set_env_var('CI', '1')
        assert self.deploy() != 0, '{}: Two regions deployed in parallel failed'.format(__name__)

    def teardown(self):
        """Teardown scaffolding."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.parallelism_test_dir):
            run_command(['runway', 'destroy'])
        self.clean()
        self.unset_env_var('CI')
