"""Test to verify behavior of explicit type declarations."""
import subprocess

from r4y.util import change_dir

from integration_tests.test_r4y_module_type_detection.test_r4y_module_type_detection import (
    RunwayModuleTypeDetection
)


class TestTypeCloudformation(RunwayModuleTypeDetection):
    """Test to verify a 'type' definition of 'cloudformation' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('type_cloudformation')
        self.copy_r4y('type-cloudformation')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['r4y', 'deploy'], stderr=subprocess.STDOUT)
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
