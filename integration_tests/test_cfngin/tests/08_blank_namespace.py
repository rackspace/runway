"""CFNgin test."""
# flake8: noqa
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestBlankNamespace(Cfngin):
    """Test CFNgin namespace as an empty string.

    Requires valid AWS credentials.

    """

    REQUIRED_FIXTURE_FILES = [
        '.'.join(basename(__file__).split('.')[:-1]) + '.yaml'
    ]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code == 0, 'exit code should be zero'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.runway_cmd('destroy')
        self.cleanup_fixtures()
