"""Test changing backends between local and S3."""
from runway.util import change_dir
from test_terraform.test_terraform import Terraform


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

        with change_dir(self.base_dir):
            return self.run_command(['runway', 'deploy'])

    def init(self):
        """Initialize test."""
        self.clean()
        self.run_stacker()
        self.set_tf_version(11)

    def run(self):
        """Run tests."""
        assert self.deploy_backend('local') == 0, '{}: Local backend failed'.format(__name__)
        assert self.deploy_backend('s3') == 0, '{}: S3 backend failed'.format(__name__)

    def teardown(self):
        """Teardown any created resources."""
        self.LOGGER.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.base_dir):
            self.run_command(['runway', 'destroy'])
        self.clean()
