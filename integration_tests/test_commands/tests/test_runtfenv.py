"""Test tfenv."""
import os
from subprocess import check_output

import boto3

from integration_tests.test_commands.test_commands import Commands

CLIENT = boto3.client('ssm')

class TestRunTFEnv(Commands):
    """Tests run-tfenv subcommand."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        pass  # pylint: disable=unnecessary-pass

    def get_path(self):
        """Gets the test path."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'tfenv')

    def run(self):
        """Run tests."""
        # init
        check_output(
            ['runway',
             'tfenv',
             'run',
             'init',
             self.get_path()]
        ).decode()

        # apply
        check_output(
            ['runway',
             'tfenv',
             'run',
             '--',
             'apply',
             '-auto-approve',
             self.get_path()
            ]
        ).decode()

        # output
        key = check_output(
            ['runway',
             'tfenv',
             'run',
             '--',
             'output',
             'key'
            ]
        ).decode()

        # ssm parameter
        parameter = CLIENT.get_parameter(Name=key)
        value = parameter['Parameter']['Value']

        # assert
        assert value == 'bar'

    def teardown(self):
        """Teardown any created resources."""
        check_output(
            ['runway',
             'tfenv',
             'run',
             '--',
             'destroy',
             '-auto-approve',
             self.get_path()
            ]
        ).decode()

        pass  # pylint: disable=unnecessary-pass
