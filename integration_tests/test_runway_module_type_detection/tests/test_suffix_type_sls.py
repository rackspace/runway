"""Test to verify behavior of directory suffix based type."""
import subprocess

from runway.util import change_dir

from integration_tests.test_runway_module_type_detection.test_runway_module_type_detection import (
    RunwayModuleTypeDetection
)


class TestSuffixTypeSLS(RunwayModuleTypeDetection):
    """Test to verify a 'type' directory suffix 'sls' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('sampleapp.sls')
        self.copy_runway('suffix-sls')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['runway', 'deploy'], stderr=subprocess.STDOUT)
            return 0 if "Skipping serverless deploy of sampleapp.sls" in out.decode() else -1

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, '{}:Directory Suffix Type SLS Failed'.format(__name__)

    def teardown(self):
        """Teardown."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.clean()
