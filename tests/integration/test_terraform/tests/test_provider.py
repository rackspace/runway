"""Test changing provider versions."""
from runway.util import change_dir
from test_terraform.test_terraform import Terraform


class ProviderTest(Terraform):
    """Test changing between provider versions."""
    TEST_NAME = __name__

    def deploy_provider(self, version):
        """Deploy provider."""
        self.copy_template('provider-version{}.tf'.format(version))
        self.copy_runway('s3')
        with change_dir(self.base_dir):
            return self.run_command(['runway', 'deploy'])

    def init(self):
        """Initialize test."""
        self.set_tf_version(11)

    def run(self):
        """Run tests."""
        assert self.deploy_provider(1) == 0, '{}: Provider version 1 failed'.format(__name__)
        assert self.deploy_provider(2) == 0, '{}: Provider version 2 failed'.format(__name__)

    def teardown(self):
        """Teardown any created resources."""
        self.LOGGER.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.base_dir):
            self.run_command(['runway', 'destroy'])
        self.clean()
