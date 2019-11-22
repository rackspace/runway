"""Test deploying stacks using tags."""
import os
from subprocess import check_output
from test_commands.test_commands import TestRunwayCommands


class TestRunPython(TestRunwayCommands):
    """Tests run-python subcommand."""

    TEST_NAME = __name__

    def init(self):
        """Initialize test."""
        pass  # pylint: disable=unnecessary-pass

    def run(self):
        """Run tests."""
        fixtures_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     'fixtures')
        with open(os.path.join(fixtures_path,
                               'buildpipeline.json'), 'r') as stream:
            expected_template = stream.read()
        generated_template = check_output(
            ['runway',
             'run-python',
             os.path.join(fixtures_path, 'buildpipeline.py')]
        ).decode()

        assert generated_template == expected_template

    def teardown(self):
        """Teardown any created resources."""
        pass  # pylint: disable=unnecessary-pass
