"""Test changing backends between local and local."""
from runway.util import change_dir
from test_terraform.test_terraform import Terraform
from util import run_command


class LocalToLocalBackend(Terraform):
    """Test changing between a speific and non-specific local backends."""

    TEST_NAME = __name__

    def deploy_backend(self, backend):
        """Deploy provider."""
        self.copy_template('{}-backend.tf'.format(backend))
        self.copy_runway('nos3')

        with change_dir(self.base_dir):
            return run_command(['runway', 'deploy'])

    def init(self):
        """Initialize test."""
        self.clean()
        self.set_tf_version(11)

    def run(self):
        """Run tests."""
        assert self.deploy_backend('no') == 0,\
            '{}: "No local backend" failed'.format(self.TEST_NAME)
        # https://github.com/hashicorp/terraform/issues/17663
        assert self.deploy_backend('local') != 0,\
            '{}: "Local backend" failed'.format(self.TEST_NAME)

    def teardown(self):
        """Teardown any created resources."""
        self.LOGGER.info('Tearing down: %s', self.TEST_NAME)
        with change_dir(self.base_dir):
            run_command(['runway', 'destroy'])
        self.clean()
