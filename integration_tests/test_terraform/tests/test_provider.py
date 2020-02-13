"""Test changing provider versions."""
from integration_tests.test_terraform.test_terraform import Terraform


class ProviderTest(Terraform):
    """Test changing between provider versions."""

    TEST_NAME = __name__

    def deploy_provider(self, version):
        """Deploy provider."""
        self.copy_template('provider-version{}.tf'.format(version))
        self.copy_runway('s3')
        code, _stdout, _stderr = self.runway_cmd('deploy')
        return code

    def run(self):
        """Run tests."""
        self.clean()
        self.set_tf_version(11)

        # deploy tf state bucket
        self.copy_runway('state')
        code, _stdout, _stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'

        assert self.deploy_provider(1) == 0, '{}: Provider version 1 failed'.format(__name__)
        assert self.deploy_provider(2) == 0, '{}: Provider version 2 failed'.format(__name__)

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
