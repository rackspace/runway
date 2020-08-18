"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin

FILE_BASENAME = ".".join(basename(__file__).split(".")[:-1])


class TestRollbackWithDependent(Cfngin):
    """Test CFNgin stack rollback with a dependent.

    Requires valid AWS credentials.

    This will take a bit of time to run (~5 min) due to needing to create
    a failed stack, allow it to rollback, and redeploy.

    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + ".yaml"]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd("deploy")
        assert code != 0, "exit code should be non-zero"
        expected_lines = [
            "dependent-rollback-parent:submitted (creating new stack)",
            # the suffix of the below log message can very based on when
            # CFN is polled b/c of how fast the test stack is
            "dependent-rollback-parent:failed",
            "dependent-rollback-child:failed (dependency has failed)",
            "The following steps failed: dependent-rollback-parent, dependent-rollback-child",
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd("destroy")
        self.cleanup_fixtures()
