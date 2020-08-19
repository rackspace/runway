"""Test that multiple CDK stacks does not prompt a failure."""
from integration_tests.test_cdk.test_cdk import CDK
from integration_tests.util import run_command
from runway.util import change_dir


class TestMultipleStacks(CDK):
    """Test deploying multiple stacks and ensure all are deployed."""

    TEST_NAME = __name__
    module_dir = "multiple-stacks-app.cdk"

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture(self.module_dir)
        self.copy_runway("multiple-stacks")
        with change_dir(self.cdk_test_dir):
            return run_command(["runway", "deploy"])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_env_var("CI", "1")
        assert self.deploy() == 0, "{}: Multiple Stacks failed".format(__name__)

    def teardown(self):
        """Teardown."""
        self.logger.info("Tearing down: %s", self.TEST_NAME)
        self.delete_venv(self.module_dir)
        with change_dir(self.cdk_test_dir):
            run_command(["runway", "destroy"])
        self.clean()
        self.unset_env_var("CI")
