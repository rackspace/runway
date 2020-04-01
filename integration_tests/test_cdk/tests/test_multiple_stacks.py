"""Test that multiple CDK stacks does not prompt a failure"""
from r4y.util import change_dir

from integration_tests.test_cdk.test_cdk import CDK
from integration_tests.util import run_command


class TestMultipleStacks(CDK):
    """Test deploying multiple stacks and ensure all are deployed"""

    TEST_NAME = __name__
    module_dir = 'multiple-stacks-app.cdk'

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture(self.module_dir)
        self.copy_r4y('multiple-stacks')
        with change_dir(self.cdk_test_dir):
            return run_command(['r4y', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_env_var('CI', '1')
        assert self.deploy() == 0, '{}: Multiple Stacks failed'.format(__name__)

    def teardown(self):
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.delete_venv(self.module_dir)
        with change_dir(self.cdk_test_dir):
            run_command(['r4y', 'destroy'])
        self.clean()
        self.unset_env_var('CI')
