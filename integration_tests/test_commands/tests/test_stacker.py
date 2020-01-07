"""Test deploying stacker."""
import os
from subprocess import check_output

from integration_tests.test_commands.test_commands import Commands


class TestRunStacker(Commands):
    """Tests run-stacker subcommand."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        pass  # pylint: disable=unnecessary-pass

    def run(self):
        """Run tests."""
        response = check_output(
            ['runway',
             'run-stacker',
             '--',
             '--version']).decode().strip()
        print(response)
        assert response == 'stacker 1.7.0'

    def teardown(self):
        """Teardown any created resources."""
        pass  # pylint: disable=unnecessary-pass
