"""Test destroying stacks using tags."""
from integration_tests.test_moduletags.test_moduletags import ModuleTags


class TestDestroy(ModuleTags):
    """Tests destroy using module tags."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        self.clean()
        self.copy_sampleapp()

    def run(self):
        """Run tests."""
        self.init()
        self.runway_cmd('deploy', [])
        assert self.runway_cmd('destroy', ['app1']) == 0
        self.check_stacks([str(num) for num in range(2, 7)])
        assert self.runway_cmd('destroy', ['app2']) == 0
        self.check_stacks([str(num) for num in range(3, 7)])
        self.runway_cmd('deploy', [])
        assert self.runway_cmd('destroy', ['group-1-4']) == 0
        self.check_stacks(['2', '3', '5', '6'])

    def teardown(self):
        """Teardown any created resources."""
        self.runway_cmd('destroy', [])
        self.clean()
