"""Test deploying stacks using tags."""
# pylint: disable=no-self-use
import os
from subprocess import check_output

from integration_tests.test_commands.test_commands import Commands


class TestRunPython(Commands):
    """Tests run-python subcommand."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""

    def run(self):
        """Run tests."""
        fixtures_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "fixtures"
        )
        with open(os.path.join(fixtures_path, "buildpipeline.json"), "r") as stream:
            expected_template = stream.read()
        generated_template = check_output(
            ["runway", "run-python", os.path.join(fixtures_path, "buildpipeline.py")]
        ).decode()

        assert generated_template == expected_template

    def teardown(self):
        """Teardown any created resources."""
