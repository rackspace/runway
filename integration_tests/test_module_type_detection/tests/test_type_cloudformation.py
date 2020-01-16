"""Test to verify behavior on declining deployment"""
import subprocess

from runway.util import change_dir

from integration_tests.test_module_type_detection.test_module_type_detection import (
    ModuleTypeDetection
)


class TestTypeCloudformation(ModuleTypeDetection):
    """Test to verify a 'type' definition of 'cloudformation' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('type_cloudformation')
        self.copy_runway('type-cloudformation')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['runway', 'deploy'], stderr=subprocess.STDOUT)
            return 0 if "Skipping stacker build" in out.decode() else -1

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, '{}: Type Declaration of Cloudformation Failed'.format(
            __name__
        )

    def teardown(self):
        """Teardown."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.clean()
