"""Testing that when CI is not set it still will launch the regions in series"""

from test_parallelism.test_parallelism import TestParallelism
from runway.util import change_dir
from util import run_command


class TestDefaultToSeries(TestParallelism):
    """Test deploying two regions in series."""

    TEST_NAME = __name__

    def __init__(self, logger):
        """Init class."""
        TestParallelism.__init__(self, logger)
        self.logger = logger

    def deploy(self):
        """Deploy provider."""
        self.copy_runway('default-to-series')
        self.copy_fixture('sampleapp.cfn')
        with change_dir(self.parallelism_test_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_environment('dev')
        assert self.deploy() == 0, '{}: Default to series failed'.format(__name__)

    def teardown(self):
        """Teardown scaffolding."""
        self.set_env_var('CI', '1')
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.parallelism_test_dir):
            run_command(['runway', 'destroy'])
        self.clean()
        self.unset_env_var('CI')
