"""Test running kbenv commands."""
import os
import tempfile
from subprocess import check_output
from integration_tests.test_commands.test_commands import Commands



class TestKBEnv(Commands):
    """Tests kbenv subcommand."""

    TEST_NAME = __name__

    tmp_stack = None

    stack_path = None

    env = None

    def init(self):
        """Initialize eks."""
        pass  # pylint: disable=unnecessary-pass

    def run(self):
        """Run tests."""

        # setup context
        tmp_root = tempfile.gettempdir()
        self.tmp_stack = tempfile.TemporaryDirectory(dir=tmp_root)
        self.stack_path = self.tmp_stack.name + '/k8s-tf-infrastructure'
        self.env = dict(
            os.environ,
            CI='1',
            DEPLOY_ENVIRONMENT='dev',
            KUBECONFIG='{0}/.kubeconfig'.format(self.stack_path))

        # create project from k8s-tf-repo sample
        check_output(
            ['runway', 'gen-sample', 'k8s-tf-repo'],
            cwd=self.tmp_stack.name
        ).decode()

        # deploy stack
        check_output(
            ['runway', 'deploy', '--tag', 'eks'],
            cwd=self.stack_path,
            env=self.env
        ).decode()

        # create kubeconfig
        response = check_output(
            ['aws', 'eks', 'update-kubeconfig', '--name', 'k8s-dev',
             '--kubeconfig', './.kubeconfig', '--region', 'us-west-2'],
            cwd=self.stack_path,
            env=self.env
        ).decode()

        # run kubectl command
        response = check_output(
            ['runway', 'kbenv', 'run', '--',
             'get', 'namespace', 'default', "--kubeconfig=./.kubeconfig"],
            cwd=self.stack_path,
            env=self.env
        ).decode()

        # check that default namespace is Active
        assert 'Active' in response

    def teardown(self):
        """Teardown any created resources."""
        check_output(
            ['runway', 'destroy', '--tag', 'eks'],
            cwd=self.stack_path,
            env=self.env
        ).decode()
        self.tmp_stack.cleanup()
