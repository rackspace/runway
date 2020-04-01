"""Test deploying stacks using tags."""
from integration_tests.test_moduletags.test_moduletags import ModuleTags


class TestDeploy(ModuleTags):
    """Tests deploy using module tags."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        self.clean()
        self.copy_sampleapp()

    def run(self):
        """Run tests."""
        self.init()
        assert self.r4y_cmd('deploy', ['app1']) == 0
        self.check_stacks(['1'])
        assert self.r4y_cmd('deploy', ['app2']) == 0
        self.check_stacks(['1', '2'])
        self.r4y_cmd('destroy', [])
        assert self.r4y_cmd('deploy', ['group-1-4']) == 0
        self.check_stacks(['1', '4'])

    def teardown(self):
        """Teardown any created resources."""
        self.r4y_cmd('destroy', [])
        self.clean()
