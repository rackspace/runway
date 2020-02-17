"""Test changing backends between local and S3."""
from integration_tests.test_terraform.test_terraform import Terraform


class LocalToS3Backend(Terraform):
    """Test changing between local and S3 backends."""

    TEST_NAME = __name__

    def deploy_backend(self, backend):
        """Deploy provider."""
        self.copy_template('{}-backend.tf'.format(backend))
        if backend == 's3':
            self.copy_runway('s3')
        else:
            self.copy_runway('nos3')
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

        assert self.deploy_backend('local') == 0, '{}: Local backend failed'.format(__name__)
        assert self.deploy_backend('s3') == 0, '{}: S3 backend failed'.format(__name__)

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
