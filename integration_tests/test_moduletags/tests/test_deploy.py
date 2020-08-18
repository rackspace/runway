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
        assert self.runway_cmd("deploy", ["app1"]) == 0
        self.check_stacks(["1"])
        assert self.runway_cmd("deploy", ["app2"]) == 0
        self.check_stacks(["1", "2"])
        self.runway_cmd("destroy", [])
        assert self.runway_cmd("deploy", ["group-1-4"]) == 0
        self.check_stacks(["1", "4"])

    def teardown(self):
        """Teardown any created resources."""
        self.runway_cmd("destroy", [])
        self.clean()
