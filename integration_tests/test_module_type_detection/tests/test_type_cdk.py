"""Test to verify behavior on declining deployment"""
import subprocess

from runway.util import change_dir

from integration_tests.test_module_type_detection.test_module_type_detection import (
    ModuleTypeDetection
)


class TestTypeCDK(ModuleTypeDetection):
    """Test to verify a 'type' definition of 'cdk' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('type_cdk')
        self.copy_runway('type-cdk')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['runway', 'deploy'], stderr=subprocess.STDOUT)
            return 0 if "Skipping cdk deploy of type_cdk" in out.decode() else -1

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, '{}: Declining Deployment failed'.format(__name__)

    def teardown(self):
        """Teardown."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.clean()
