"""Test getting current user."""
import os
import json

from subprocess import check_output
from integration_tests.test_commands.test_commands import Commands


class TestRunAWS(Commands):
    """Tests run-aws subcommand."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        pass  # pylint: disable=unnecessary-pass

    def run(self):
        """Run test."""
        response = check_output(
            ['runway',
             'run-aws',
             'sts',
             'get-caller-identity']
        ).decode()
        data = json.loads(response)
        assert 'Arn' in data, 'response has no Arn property'

    def teardown(self):
        """Teardown any created resources."""
        pass  # pylint: disable=unnecessary-pass
