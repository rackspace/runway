"""Test to verify behavior of directory suffix based type"""
import subprocess

from runway.util import change_dir

from integration_tests.test_runway_module_type_detection.test_runway_module_type_detection import (
    RunwayModuleTypeDetection
)


class TestSuffixTypeK8S(RunwayModuleTypeDetection):
    """Test to verify a 'type' directory suffix 'k8s' is respected."""

    TEST_NAME = __name__

    def deploy(self):
        """Deploy provider."""
        self.copy_fixture('sampleapp.k8s')
        self.copy_runway('suffix-k8s')
        with change_dir(self.mtd_test_dir):
            out = subprocess.check_output(['runway', 'deploy'], stderr=subprocess.STDOUT)
            return 0 if "No kustomize overlay for this environment" in out.decode() else -1

    def run(self):
        """Run tests."""
        self.clean()
        assert self.deploy() == 0, '{}:Directory Suffix Type CDK Failed'.format(__name__)

    def teardown(self):
        """Teardown."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        self.clean()
