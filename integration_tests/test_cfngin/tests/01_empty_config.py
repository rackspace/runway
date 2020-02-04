"""CFNgin test."""
# pylint: disable=invalid-name
from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestEmptyConfig(Cfngin):
    """Test CFNgin with an empty config file."""

    REQUIRED_FIXTURE_FILES = [
        '01-empty-config.yaml'
    ]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        assert code != 0
        assert 'runway.cfngin.exceptions.InvalidConfig' in stderr

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.cleanup_fixtures()
