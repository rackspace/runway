"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin

FILE_BASENAME = ".".join(basename(__file__).split(".")[:-1])


class DestroyRemoved(Cfngin):
    """Test CFNgin persistent graph destroying removed stacks.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + ".1.yaml", FILE_BASENAME + ".2.yaml"]
    TEST_NAME = __name__

    def _build(self):
        """Execute and assert initial build."""
        code, _stdout, stderr = self.runway_cmd("deploy")
        assert code == 0, "exit code should be zero"
        expected_lines = [
            "other:removed from the CFNgin config file; it is being destroyed",
            "other:submitted (submitted for destruction)",
            "other:complete (stack destroyed)",
        ]
        for stack in ["vpc", "bastion", "other"]:
            expected_lines.append(f"{stack}:submitted (creating new stack)")
            expected_lines.append(f"{stack}:complete (creating new stack)")
            if stack != "other":
                expected_lines.append(f"{stack}:skipped (nochange)")
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        self._build()

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd("destroy")
        self.cleanup_fixtures()
