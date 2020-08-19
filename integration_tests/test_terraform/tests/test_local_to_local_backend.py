"""Test changing backends between local and local."""
from integration_tests.test_terraform.test_terraform import Terraform


class LocalToLocalBackend(Terraform):
    """Test changing between a specific and non-specific local backends."""

    TEST_NAME = __name__

    def deploy_backend(self, backend):
        """Deploy provider."""
        self.copy_template("{}-backend.tf".format(backend))
        self.copy_runway("nos3")
        code, _stdout, _stderr = self.runway_cmd("deploy")
        return code

    def run(self):
        """Run tests."""
        self.clean()
        self.set_tf_version(11)

        assert self.deploy_backend("no") == 0, '{}: "No local backend" failed'.format(
            self.TEST_NAME
        )
        # https://github.com/hashicorp/terraform/issues/17663
        assert self.deploy_backend("local") != 0, '{}: "Local backend" failed'.format(
            self.TEST_NAME
        )

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info("Tearing down: %s", self.TEST_NAME)
        code, _stdout, _stderr = self.runway_cmd("destroy")
        assert code == 0, "exit code should be zero"
        self.clean()
