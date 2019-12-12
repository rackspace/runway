"""Test that multiple CDK stacks does not prompt a failure"""
from test_cdk.test_cdk import TestCDK
from runway.util import change_dir
from util import run_command


class TestMultipleStacks(TestCDK):
    """Test deploying multiple stacks and ensure all are deployed"""

    TEST_NAME = __name__

    def __init__(self, logger):
        TestCDK.__init__(self, logger)
        """Init class."""
        self.logger = logger

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('multiple-stacks-app.cdk')
        self.copy_runway('multiple-stacks')
        with change_dir(self.cdk_test_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_env_var('CI', '1')
        assert self.deploy() == 0, '{}: Multiple Stacks failed'.format(__name__)

    def teardown(self):
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.cdk_test_dir):
            run_command(['runway', 'destroy'])
        self.clean()
        self.unset_env_var('CI')
