"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestLockedStack(Cfngin):
    """Test CFNgin with a locked stack.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [
        '.'.join(basename(__file__).split('.')[:-1]) + '.1.yaml',
        '.'.join(basename(__file__).split('.')[:-1]) + '.2.yaml'
    ]
    TEST_NAME = __name__

    def _build(self):
        """Execute and assert initial build."""
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'
        assert 'Using default AWS provider mode' in stderr, \
            'should use "default AWS provider mode"'
        assert 'vpc: submitted (creating new stack)' in stderr, \
            'should log that the vpc stack has been submitted (build)'
        assert 'vpc: complete (creating new stack)' in stderr, \
            'should log that the vpc stack has completed (build)'

    def _update_no_change(self):
        """Execute and assert second build with no changes."""
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'
        assert 'Using default AWS provider mode' in stderr, \
            'should use "default AWS provider mode"'
        assert 'vpc: skipped (nochange)' in stderr, \
            'should log no change for vpc'

    def _destroy(self):
        """Execute and assert destroy."""
        code, _stdout, stderr = self.runway_cmd('destroy')
        assert code == 0, 'exit code should be zero'
        assert 'vpc: submitted (submitted for destruction)' in stderr, \
            'should log that the vpc stack has been submitted (destroy)'
        assert 'vpc: complete (stack destroyed)' in stderr, \
            'should log that the vpc stack has completed (destroy)'

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'
        expected_lines = [
            'Using default AWS provider mode',
            'vpc: submitted (creating new stack)',
            'vpc: complete (creating new stack)',
            'vpc: skipped (locked)',
            'bastion: submitted (creating new stack)',
            'bastion: complete (creating new stack)'
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd('destroy')  # cleanup incase of failure
        self.cleanup_fixtures()
