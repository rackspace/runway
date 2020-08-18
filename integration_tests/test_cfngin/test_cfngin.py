"""Integration tests for runway.cfngin."""
from integration_tests.integration_test import IntegrationTest
from integration_tests.util import execute_tests, import_tests


class Cfngin(IntegrationTest):
    """Test runner for CFNgin."""

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, "[0-9][0-9]_**")
        self.set_environment("dev")
        self.set_env_var("CI", "1")
        tests = [
            test(self.logger, self.environment) for test in Cfngin.__subclasses__()
        ]
        if not tests:
            raise Exception("No tests were found.")
        self.logger.debug("FOUND TESTS: %s", tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.unset_env_var("CI")
        self.logger.debug(
            "Teardown is defined in the submodules, not "
            'the "TestCfngin" parent class.'
        )
