"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
import os.path
from os.path import basename

from send2trash import send2trash

from integration_tests.test_cfngin.test_cfngin import Cfngin

FILE_BASENAME = '.'.join(basename(__file__).split('.')[:-1])


class TestRecreateFailed(Cfngin):
    """Test CFNgin recreation of a failed stack.

    Requires valid AWS credentials.

    This will take a bit of time to run (~5 min) due to needing to create
    a failed stack, allow it to rollback, and redeploy.

    """

    REQUIRED_FIXTURE_FILES = [FILE_BASENAME + '.1.yaml',
                              FILE_BASENAME + '.2.yaml']
    TEST_NAME = __name__

    def _deploy_bad(self):
        """Deploy failing config."""
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code != 0, 'exit code should be non-zero since one config failed'
        expected_lines = [
            'recreate-failed: submitted (creating new stack)',
            'recreate-failed: submitted (rolling back new stack)',
            'recreate-failed: failed (rolled back new stack)',
            'The following steps failed: recreate-failed'
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def _deploy_good(self):
        """Deploy good config."""
        # get rid of the bad config so the good one can run
        send2trash(os.path.join(self.working_dir, FILE_BASENAME + '.1.yaml'))
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'
        expected_lines = [
            'recreate-failed: submitted (destroying stack for re-creation)',
            'recreate-failed: submitted (creating new stack)',
            'recreate-failed: complete (creating new stack)'
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        self._deploy_bad()
        self._deploy_good()

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd('destroy')
        self.cleanup_fixtures()
