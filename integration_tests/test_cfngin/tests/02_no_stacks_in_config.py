"""CFNgin test."""
# pylint: disable=invalid-name
from integration_tests.test_cfngin.test_cfngin import Cfngin


class TestNoStacksInConfig(Cfngin):
    """Test CFNgin with no stacks in config file."""

    REQUIRED_FIXTURE_FILES = [
        '02-no-stacks-in-config.yaml'
    ]
    TEST_NAME = __name__

    def run(self):
        """Run the test."""
        self.copy_fixtures()
        code, _stdout, stderr = self.runway_cmd('deploy')
        self.logger.info('stderr:\n%s', stderr)
        assert code == 0, 'exit code should be zero'
        assert 'WARNING: No stacks detected (error in config?)' in stderr, \
            'should warn when stacks are not defined in config'

    def teardown(self):
        """Teardown any created resources and delete files."""
        self.cleanup_fixtures()
