"""Test changing terraform versions."""
from integration_tests.test_terraform.test_terraform import Terraform


class VersionTest(Terraform):
    """Test changing between terraform versions."""

    TEST_NAME = __name__

    def deploy_version(self, version):
        """Deploy provider."""
        self.set_tf_version(version)
        self.copy_template('s3-backend.tf')
        self.copy_runway('s3')
        code, _stdout, _stderr = self.runway_cmd('deploy')
        return code

    def run(self):
        """Run tests."""
        self.clean()

        # deploy tf state bucket
        self.copy_runway('state')
        code, _stdout, _stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'

        assert self.deploy_version(11) == 0, '{}: Terraform version 11 failed'.format(__name__)
        assert self.deploy_version(12) == 0, '{}: Terraform version 12 failed'.format(__name__)

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        code, _stdout, _stderr = self.runway_cmd('destroy')
        assert code == 0, 'exit code should be zero'

        # destroy tf state bucket
        self.copy_runway('state')
        code, _stdout, _stderr = self.runway_cmd('destroy')
        assert code == 0, 'exit code should be zero'

        self.clean()
