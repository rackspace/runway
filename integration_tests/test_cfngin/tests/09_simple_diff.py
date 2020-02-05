"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestSimpleDiff(Cfngin):
    """Test CFNgin diff.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [
        '.'.join(basename(__file__).split('.')[:-1]) + '.yaml'
    ]
    TEST_NAME = __name__

    def _build(self):
        """Execute and assert initial build."""
        code, _stdout, _stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'

    def _diff(self):
        """Execute and assert second build with no changes."""
        self.set_environment('dev2')
        code, _stdout, stderr = self.runway_cmd('plan')
        assert code == 0, 'exit code should be zero'
        expected_lines = [
            '-InstanceType = m5.large',
            '+InstanceType = m5.xlarge',
            '- ResourceChange:',
            '    Action: Add',
            '    LogicalResourceId: VPC1',
            '    ResourceType: AWS::CloudFormation::WaitConditionHandle'
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
        self.runway_cmd('destroy')  # cleanup incase of failure
        self.cleanup_fixtures()
