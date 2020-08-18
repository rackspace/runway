"""Test deploying stacker."""
# pylint: disable=no-self-use
import os
from subprocess import check_output

import boto3

from integration_tests.test_commands.test_commands import Commands

KEY = "/runway/integration-test/stacker"
VALUE = "foo"


class TestRunStacker(Commands):
    """Tests run-stacker subcommand."""

    TEST_NAME = __name__

    def get_stack_path(self):
        """Get the stacker test path."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "fixtures", "stacker"
        )

    def init(self):
        """Initialize test."""

    def run(self):
        """Run tests."""
        path = self.get_stack_path()
        check_output(
            ["runway", "run-stacker", "--", "build", "stack.yaml"], cwd=path
        ).decode()
        client = boto3.client("ssm", region_name=self.environment["AWS_DEFAULT_REGION"])
        parameter = client.get_parameter(Name=KEY)
        assert parameter["Parameter"]["Value"] == VALUE

    def teardown(self):
        """Teardown any created resources."""
        path = self.get_stack_path()
        check_output(
            ["runway", "run-stacker", "--", "destroy", "stack.yaml", "--force"],
            cwd=path,
        ).decode()
