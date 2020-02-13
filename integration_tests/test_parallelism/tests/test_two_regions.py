"""Test that two regions can be deployed in parallel."""
from runway.util import change_dir

from integration_tests.test_parallelism.test_parallelism import Parallelism
from integration_tests.util import run_command


class TestTwoRegions(Parallelism):
    """Test deploying two regions in parallel."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('sampleapp.cfn')
        self.copy_runway('two-regions')
        with change_dir(self.parallelism_test_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_env_var('CI', '1')
        assert self.deploy() == 0, '{}: Two regions deployed in parallel failed'.format(__name__)

    def teardown(self):
        """Teardown scaffolding."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.parallelism_test_dir):
            run_command(['runway', 'destroy'])
        self.clean()
