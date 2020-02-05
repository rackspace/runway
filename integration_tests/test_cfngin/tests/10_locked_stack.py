"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin

FILE_BASENAME = '.'.join(basename(__file__).split('.')[:-1])


class TestLockedStack(Cfngin):
    """Test CFNgin with a locked stack.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [
        FILE_BASENAME + '.1.yaml',
        FILE_BASENAME + '.2.yaml'
    ]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'
        expected_lines = [
            'Using default AWS provider mode',
            'locked-stack-vpc: submitted (creating new stack)',
            'locked-stack-vpc: complete (creating new stack)',
            'locked-stack-vpc: skipped (locked)',
            'locked-stack-bastion: submitted (creating new stack)',
            'locked-stack-bastion: complete (creating new stack)'
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd('destroy')  # cleanup incase of failure
        self.cleanup_fixtures()
