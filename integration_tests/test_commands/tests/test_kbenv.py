"""Test running kbenv commands."""
import os
from subprocess import check_output

from integration_tests.test_commands.test_commands import Commands


class TestKBEnv(Commands):
    """Tests kbenv subcommand."""

    TEST_NAME = __name__

    def get_stack_path(self):
        """Gets the stack path."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'kbenv')

    def init(self):
        """Initialize eks."""
        pass  # pylint: disable=unnecessary-pass

    def run(self):
        """Run tests."""
        path = self.get_stack_path()
        env = dict(os.environ, KUBECONFIG='{0}/.kubeconfig'.format(path))
        # init
        check_output(
            ['runway', 'tfenv', 'run', 'init'],
            cwd=path
        ).decode()
        # apply
        check_output(
            ['runway', 'tfenv', 'run', '--', 'apply', '-auto-approve'],
            cwd=path
        ).decode()
        # get cluster name
        cluster = check_output(
            ['runway', 'tfenv', 'run', '--', 'output', 'cluster_arn'],
            cwd=path
        ).decode().strip()
        # run kubectl command
        response = check_output(
            ['runway', 'kbenv', 'run', '--', 
             'get', 'namespace', 'default', "--cluster={0}".format(cluster)],
            cwd=path,
            env=env
        ).decode()
        # check that default namespace is Active
        assert 'Active' in response

    def teardown(self):
        """Teardown any created resources."""
        # apply
        check_output(
            ['runway', 'tfenv', 'run', '--', 'destroy', '-auto-approve'],
            cwd=self.get_stack_path()
        ).decode()
