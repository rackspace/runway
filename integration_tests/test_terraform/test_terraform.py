"""Tests for Terraform."""
import glob
import os

from send2trash import send2trash

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import copy_file, execute_tests, import_tests


class Terraform(IntegrationTest):
    """Base class for all Terraform testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, "templates")

    tf_test_dir = os.path.join(base_dir, "terraform_test.tf")
    tf_state_dir = os.path.join(base_dir, "tf_state.cfn")

    def copy_runway(self, template):
        """Copy runway template to proper directory."""
        template_file = os.path.join(
            self.template_dir, "runway-{}.yml".format(template)
        )
        copy_file(template_file, os.path.join(self.base_dir, "runway.yml"))

    def copy_template(self, template, name="main.tf"):
        """Copy template to Terraform module folder."""
        template_file = os.path.join(self.template_dir, template)
        copy_file(template_file, os.path.join(self.tf_test_dir, name))

    def clean(self):
        """Clean up Terraform module directory."""
        file_types = ("*.tf", ".terraform-version", "*.yml", "local_backend")
        templates = []
        for file_type in file_types:
            templates.extend(glob.glob(os.path.join(self.tf_test_dir, file_type)))
            templates.extend(glob.glob(os.path.join(self.base_dir, file_type)))

        for template in templates:
            if os.path.isfile(template):
                self.logger.debug('send2trash: "%s"', template)
                send2trash(template)
        folders = (".terraform", "terraform.tfstate.d")
        for folder in folders:
            folder_path = os.path.join(self.tf_test_dir, folder)
            if os.path.isdir(folder_path):
                self.logger.debug('send2trash: "%s"', folder_path)
                send2trash(folder_path)

    def set_tf_version(self, version=11):
        """Copy version file to module directory."""
        version_file = "tf-v{}.version".format(version)
        self.copy_template(version_file, ".terraform-version")

    def run(self):
        """Find all Terraform tests and run them."""
        import_tests(self.logger, self.tests_dir, "test_*")
        self.set_environment("dev")
        self.set_env_var("CI", "1")
        tests = [
            test(self.logger, self.environment) for test in Terraform.__subclasses__()
        ]
        if not tests:
            raise Exception("No tests were found.")
        self.logger.debug("FOUND TESTS: %s", tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.clean()
