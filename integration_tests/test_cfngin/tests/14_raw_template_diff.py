"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin

FILE_BASENAME = ".".join(basename(__file__).split(".")[:-1])


class TestRawTemplateDiff(Cfngin):
    """Test CFNgin diff using a raw template.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + ".yaml"]
    TEST_NAME = __name__

    def _build(self):
        """Execute and assert initial build."""
        self.set_environment("dev")
        code, _stdout, _stderr = self.runway_cmd("deploy")
        assert code == 0, "exit code should be zero"

    def _diff(self):
        """Execute and assert second build with no changes."""
        self.set_environment("dev2")
        code, _stdout, stderr = self.runway_cmd("plan")
        assert code == 0, "exit code should be zero"
        expected_lines = [
            "-WaitConditionCount = 1",
            "+WaitConditionCount = 2",
            "- ResourceChange:",
            "    Action: Add",
            "    LogicalResourceId: Dummy2",
            "    ResourceType: AWS::CloudFormation::WaitConditionHandle",
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        self._build()
        self._diff()

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd("destroy")
        self.cleanup_fixtures()
