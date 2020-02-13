"""Test to verify behavior of explicit type declarations."""
import subprocess

from runway.util import change_dir

from integration_tests.test_runway_module_type_detection.test_runway_module_type_detection import (
    RunwayModuleTypeDetection
)


class TestTypeServerless(RunwayModuleTypeDetection):
    """Test to verify a 'type' definition of 'serverless' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('type_serverless')
        self.copy_runway('type-serverless')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['runway', 'deploy'], stderr=subprocess.STDOUT)
            return 0 if "Skipping serverless deploy of type_serverless" in out.decode() else -1

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, '{}: Type Declaration of Serverless Failed'.format(
            __name__
        )

    def teardown(self):
        """Teardown."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.clean()
