"""Test changing backends between local and S3."""
from runway.util import change_dir
from integration_tests.test_terraform.test_terraform import Terraform
from integration_tests.util import run_command


class LocalToS3Backend(Terraform):
    """Test changing between local and S3 backends."""

    TEST_NAME = __name__

    def __init__(self, logger):
        """Init class."""
        Terraform.__init__(self, logger)
        self.logger = logger

    def deploy_backend(self, backend):
        """Deploy provider."""
        self.copy_template('{}-backend.tf'.format(backend))
        if backend == 's3':
            self.copy_runway('s3')
        else:
            self.copy_runway('nos3')

        with change_dir(self.base_dir):
            return run_command(['runway', 'deploy'])

    def run(self):
        """Run tests."""
        self.clean()
        self.set_env_var('CI', '1')
        self.run_stacker()
        self.set_tf_version(11)

        assert self.deploy_backend('local') == 0, '{}: Local backend failed'.format(__name__)
        assert self.deploy_backend('s3') == 0, '{}: S3 backend failed'.format(__name__)

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.base_dir):
            run_command(['runway', 'destroy'])
        self.unset_env_var('CI')
        self.clean()
