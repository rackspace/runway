"""CFNgin test."""
# pylint: disable=invalid-name
from os.path import basename

from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestNoNamespace(Cfngin):
    """Test CFNgin with no namespace."""

    REQUIRED_FIXTURE_FILES = [
        '.'.join(basename(__file__).split('.')[:-1]) + '.yaml'
    ]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code != 0, 'exit code should be non-zero'
        expected_lines = [
            'This field is required'
        ]
        for line in expected_lines:
            assert line in stderr, f'"{line}" missing from output'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.cleanup_fixtures()
