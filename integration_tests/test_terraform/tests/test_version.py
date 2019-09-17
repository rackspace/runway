"""Test changing terraform versions."""
from runway.util import change_dir
from test_terraform.test_terraform import Terraform
from util import run_command


class VersionTest(Terraform):
    """Test changing between terraform versions."""

    TEST_NAME = __name__

    def deploy_version(self, version):
        """Deploy provider."""
        self.set_tf_version(version)
        self.copy_template('s3-backend.tf')
        self.copy_runway('s3')
        with change_dir(self.base_dir):
            return run_command(['runway', 'deploy'])

    def init(self):
        """Initialize test."""
        self.clean()
        self.run_stacker()

    def run(self):
        """Run tests."""
        assert self.deploy_version(11) == 0, '{}: Terraform version 11 failed'.format(__name__)
        assert self.deploy_version(12) == 0, '{}: Terraform version 12 failed'.format(__name__)

    def teardown(self):
        """Teardown any created resources."""
        self.LOGGER.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.base_dir):
            run_command(['runway', 'destroy'])
        self.clean()
