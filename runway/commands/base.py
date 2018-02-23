"""runway base module."""
from __future__ import print_function

from contextlib import contextmanager
from subprocess import check_call, check_output

import logging
import os
import shutil
import stat
import sys

import yaml

# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from ..embedded.stacker.awscli_yamlhelper import yaml_parse as parse_cloudformation_template  # noqa
from .. import __version__ as version

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger('runway')
EMBEDDED_LIB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'embedded'
)


class Base(object):  # noqa pylint: disable=too-many-public-methods
    """Base class for deployer classes."""

    def __init__(self, options, env_vars=None, env_root=None,  # noqa pylint: disable=too-many-arguments
                 module_root=None, runway_config_dir=None):
        """Initialize base class."""
        self.options = options

        if env_vars is None:
            self.env_vars = os.environ.copy()
        else:
            self.env_vars = env_vars

        if env_root is None:
            self.env_root = os.getcwd()
        else:
            self.env_root = env_root

        self.module_root = module_root

        if runway_config_dir is None:
            self.runway_config_path = os.path.join(
                self.env_root,
                'runway.yml'
            )
        else:
            self.runway_config_path = os.path.join(
                runway_config_dir,
                'runway.yml'
            )
        self._runway_config = None

        self.environment_override_name = 'DEPLOY_ENVIRONMENT'

    def update_env_vars(self, val):
        """Update env_vars dict with provided dict."""
        for key, value in list(val.items()):
            self.env_vars[key] = value

    def get_env_dirs(self):
        """Return list of directories in env_root."""
        repo_dirs = os.walk(self.env_root).next()[1]
        if '.git' in repo_dirs:
            repo_dirs.remove('.git')  # not relevant for any repo operations
        return repo_dirs

    def lint(self, base_dir=None, dirs_to_scan=None):
        """Call code linters."""
        from flake8.main import application as flake8_app
        from yamllint.cli import run as yamllint_run

        if base_dir is None:
            base_dir = self.env_root
        if dirs_to_scan is None:
            dirs_to_scan = self.get_env_dirs()

        if os.path.isfile(os.path.join(base_dir, '.yamllint.yml')):
            yamllint_config = os.path.join(base_dir, '.yamllint.yml')
        else:
            yamllint_config = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'templates',
                '.yamllint.yml'
            )
        with self.change_dir(base_dir):
            flake8_run = flake8_app.Application()
            flake8_run.run(['--exclude=node_modules'] + dirs_to_scan)
            with self.ignore_exit_code_0():
                yamllint_run(
                    ["--config-file=%s" % yamllint_config] + dirs_to_scan
                )

    def get_cookbook_dirs(self, base_dir=None):
        """Find cookbook directories."""
        if base_dir is None:
            base_dir = self.env_root

        cookbook_dirs = []
        dirs_to_skip = set(['.git'])
        for root, dirs, files in os.walk(base_dir):  # pylint: disable=W0612
            dirs[:] = [d for d in dirs if d not in dirs_to_skip]
            for name in files:
                if name == 'metadata.rb':
                    if 'cookbook' in os.path.basename(os.path.dirname(root)):
                        cookbook_dirs.append(root)
        return cookbook_dirs

    def cookbook_tests(self, base_dir=None):
        """Run cookbook tests."""
        if base_dir is None:
            base_dir = self.env_root

        cookbook_dirs = self.get_cookbook_dirs(base_dir)

        if cookbook_dirs:
            if self.which('foodcritic') is None \
                    or self.which('cookstyle') is None:
                LOGGER.error('"foodcritic" and/or "cookstyle" not found -- '
                             'please ensure ChefDK is installed.')
                sys.exit(1)

            for path in cookbook_dirs:
                check_call(['foodcritic', '-f any', path])
                check_call(['cookstyle', '-P', path])

    def python_tests(self, base_dir=None, pylint_rc_file=None):  # noqa pylint: disable=too-many-branches,too-many-locals
        """Run python tests."""
        from pylint.lint import Run as PylintRun

        if base_dir is None:
            base_dir = self.env_root
        if pylint_rc_file is None:
            if os.path.isfile(os.path.join(base_dir, '.pylintrc')):
                pylint_rc_config = [
                    "--rcfile=%s" % os.path.join(base_dir, '.pylintrc')
                ]
            else:
                pylint_rc_config = []

        # Ensure python 'Makefiles' are executable
        for directory in os.listdir(base_dir):
            dir_path = os.path.join(base_dir, directory)
            if not os.path.isdir(dir_path):
                continue
            makefile_path = os.path.join(dir_path, 'Makefile.py')
            if os.path.isfile(makefile_path):
                self.ensure_file_is_executable(makefile_path)

        # Check all python files in repo
        dirs_to_skip = set(['.git',
                            'node_modules'])
        for root, dirs, files in os.walk(base_dir):  # noqa pylint: disable=too-many-nested-blocks
            dirs[:] = [d for d in dirs if d not in dirs_to_skip]
            for name in files:
                if name[-3:] == ".py":
                    filepath = os.path.join(root, name)
                    with self.use_embedded_pkgs():  # for embedded stacker
                        with self.ignore_exit_code_0():
                            PylintRun(pylint_rc_config + ['-E',  # ignore warn
                                                          filepath])
                    # Blueprints should output their template when executed
                    if (root.endswith('blueprints') and
                            not filepath.endswith('__init__.py')):
                        self.ensure_file_is_executable(filepath)
                        try:
                            shell_out_env = os.environ.copy()
                            if 'PYTHONPATH' in shell_out_env:
                                shell_out_env['PYTHONPATH'] = (
                                    "%s:%s" % (EMBEDDED_LIB_PATH,
                                               shell_out_env['PYTHONPATH'])
                                )
                            else:
                                shell_out_env['PYTHONPATH'] = EMBEDDED_LIB_PATH
                            cfn_template = check_output(
                                [sys.executable, filepath],
                                env=shell_out_env
                            )
                            if cfn_template == '':
                                raise ValueError("Template output should not "
                                                 "be empty!")
                            parse_cloudformation_template(cfn_template)
                        except:  # noqa - Bare except fine in this context
                            print("Error while checking %s for valid "
                                  "YAML/JSON output" % filepath)
                            raise

    def test(self):
        """Execute tests."""
        self.lint()
        self.cookbook_tests()
        self.python_tests()

    def save_existing_iam_env_vars(self):
        """Backup IAM environment variables for later restoration."""
        for i in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                  'AWS_SESSION_TOKEN']:
            if i in self.env_vars:
                self.update_env_vars({'OLD_' + i: self.env_vars[i]})

    def restore_existing_iam_env_vars(self):
        """Restore backed up IAM environment variables."""
        for i in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                  'AWS_SESSION_TOKEN']:
            if 'OLD_' + i in self.env_vars:
                self.update_env_vars({i: self.env_vars['OLD_' + i]})
            elif i in self.env_vars:
                self.env_vars.pop(i)

    def assume_role(self, role_arn, session_name=None, region='us-east-1'):
        """Assume IAM role."""
        import boto3
        if session_name is None:
            session_name = 'runway'
        sts_client = boto3.client('sts', region_name=region)
        LOGGER.info("Assuming role %s...", role_arn)
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name
        )
        self.update_env_vars(
            {'AWS_ACCESS_KEY_ID': response['Credentials']['AccessKeyId'],
             'AWS_SECRET_ACCESS_KEY': response['Credentials']['SecretAccessKey'],  # noqa
             'AWS_SESSION_TOKEN': response['Credentials']['SessionToken']}
        )

    def pre_deploy_assume_role(self, assume_role_config, region):
        """Assume role (prior to deployment)."""
        if isinstance(assume_role_config, dict):
            if assume_role_config.get('post_deploy_env_revert'):
                self.save_existing_iam_env_vars()
            if assume_role_config.get('session_name'):
                self.assume_role(
                    role_arn=assume_role_config['arn'],
                    session_name=assume_role_config['session_name'],
                    region=region
                )
            else:
                self.assume_role(role_arn=assume_role_config['arn'],
                                 region=region)
        else:
            self.assume_role(role_arn=assume_role_config, region=region)

    def post_deploy_assume_role(self, assume_role_config):
        """Assume role (prior to deployment)."""
        if isinstance(assume_role_config, dict):
            if assume_role_config.get('post_deploy_env_revert'):
                self.restore_existing_iam_env_vars()

    def path_only_contains_dirs(self, path):
        """Return boolean on whether a path only contains directories."""
        pathlistdir = os.listdir(path)
        if pathlistdir == []:
            return True
        elif any(os.path.isfile(os.path.join(path, i)) for i in pathlistdir):
            return False
        return all(self.path_only_contains_dirs(os.path.join(path, i)) for i in pathlistdir)  # noqa

    def get_empty_dirs(self, path):
        """Return a list of empty directories in path."""
        empty_dirs = []
        for i in os.listdir(path):
            child_path = os.path.join(path, i)
            if i == '.git' or os.path.isfile(child_path) or os.path.islink(child_path):  # noqa
                continue
            if self.path_only_contains_dirs(child_path):
                empty_dirs.append(i)
        return empty_dirs

    def generate_sample_sls_module(self, module_dir=None):
        """Generate skeleton Serverless sample module."""
        if module_dir is None:
            module_dir = os.path.join(self.env_root, 'sampleapp.sls')
        self.generate_sample_module(module_dir)
        for i in ['config-dev-us-east-1.json', 'handler.py', 'package.json',
                  'serverless.yml']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'serverless',
                             i),
                os.path.join(module_dir, i),
            )
        LOGGER.info("Sample Serverless module created at %s",
                    module_dir)

    def generate_sample_cfn_module(self, module_dir=None):
        """Generate skeleton CloudFormation sample module."""
        if module_dir is None:
            module_dir = os.path.join(self.env_root, 'sampleapp.cfn')
        self.generate_sample_module(module_dir)
        for i in ['01-sampleapp.yaml', 'dev-us-east-1.env']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'cfn',
                             i),
                os.path.join(module_dir, i)
            )
        os.mkdir(os.path.join(module_dir, 'templates'))
        shutil.copyfile(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         'templates',
                         'cfn',
                         'templates',
                         'bucket.json'),
            os.path.join(module_dir, 'templates', 'bucket.json')
        )
        LOGGER.info("Sample CloudFormation module created at %s",
                    module_dir)

    def generate_sample_stacker_module(self, module_dir=None):
        """Generate skeleton Stacker sample module."""
        if module_dir is None:
            module_dir = os.path.join(self.env_root, 'sampleapp.cfn')
        self.generate_sample_module(module_dir)
        for i in ['01-sampleapp.yaml', 'dev-us-east-1.env']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'stacker',
                             i),
                os.path.join(module_dir, i)
            )
        for i in ['sampleapp_blueprints', 'templates']:
            os.mkdir(os.path.join(module_dir, i))
        for i in list({'sampleapp_blueprints': ['__init__.py', 'bucket.py'],
                       'templates': ['bucket.json']}.items()):
            for template in i[1]:
                shutil.copyfile(
                    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'templates',
                                 'stacker',
                                 i[0],
                                 template),
                    os.path.join(module_dir, i[0], template)
                )
        os.chmod(  # make blueprint executable
            os.path.join(module_dir, 'sampleapp_blueprints', 'bucket.py'),
            os.stat(os.path.join(module_dir,
                                 'sampleapp_blueprints',
                                 'bucket.py')).st_mode | 0111
        )
        LOGGER.info("Sample Stacker module created at %s",
                    module_dir)

    def generate_sample_tf_module(self, module_dir=None):
        """Generate skeleton Terraform sample module."""
        if module_dir is None:
            module_dir = os.path.join(self.env_root, 'sampleapp.tf')
        self.generate_sample_module(module_dir)
        for i in ['backend.tfvars', 'dev-us-east-1.tfvars', 'main.tf']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'terraform',
                             i),
                os.path.join(module_dir, i),
            )
        LOGGER.info("Sample Terraform app created at %s",
                    module_dir)

    def parse_runway_config(self):
        """Read and parse runway.yml."""
        if os.path.isfile(self.runway_config_path):
            with open(self.runway_config_path) as data_file:
                return yaml.safe_load(data_file)
        else:
            LOGGER.error("Runway config file was not found (looking for "
                         "%s)",
                         self.runway_config_path)
            sys.exit(1)

    def execute(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the execute() method '
                                  'yourself!')

    @property
    def runway_config(self):
        """Return parsed runway.yml."""
        if not self._runway_config:
            self._runway_config = self.parse_runway_config()
        return self._runway_config

    @staticmethod
    def version():
        """Show current package version."""
        print(version)

    @staticmethod
    def which(program):
        """Mimic 'which' command behavior.

        Adapted from https://stackoverflow.com/a/377028
        """
        def is_exe(fpath):
            """Determine if program exists and is executable."""
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, _fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

        return None

    @staticmethod
    def generate_sample_module(module_dir):
        """Generate skeleton sample module."""
        if os.path.isdir(module_dir):
            LOGGER.error("Error generating sample module -- directory %s "
                         "already exists!",
                         module_dir)
            sys.exit(1)
        os.mkdir(module_dir)

    @staticmethod
    def ensure_file_is_executable(path):
        """Exit if file is not executable."""
        if not stat.S_IXUSR & os.stat(path)[stat.ST_MODE]:
            print("Error: File %s is not executable" % path)
            sys.exit(1)

    @staticmethod
    @contextmanager
    def change_dir(newdir):
        """Change directory.

        Adapted from http://stackoverflow.com/a/24176022

        """
        prevdir = os.getcwd()
        os.chdir(os.path.expanduser(newdir))
        try:
            yield
        finally:
            os.chdir(prevdir)

    @staticmethod
    @contextmanager
    def override_sysargv(new_args=None):
        """Temporarily spoof the arguments provided in calling the application.

        Some applications will only detect their configuration from the command
        line. A list provided to this method will override what they detect.

        """
        if new_args is None:
            new_args = []
        orig_args = sys.argv
        sys.argv = new_args
        try:
            yield
        finally:
            sys.argv = orig_args

    @staticmethod
    @contextmanager
    def turn_down_stacker_logging(command):
        """Disable duplicate Stacker logging."""
        stacker_loggers = [
            'runway.embedded.stacker.actions.diff',
            'runway.embedded.stacker.commands.stacker',
            'runway.embedded.stacker.plan'
        ]
        if command == 'diff':
            try:
                for i in stacker_loggers:
                    logging.getLogger(i).setLevel(logging.ERROR)
                yield
            finally:
                for i in stacker_loggers:
                    logging.getLogger(i).setLevel(logging.INFO)
        else:
            yield

    @staticmethod
    @contextmanager
    def use_embedded_pkgs():
        """Temporarily prepend embedded packages to sys.path."""
        old_sys_path = sys.path
        sys.path.insert(
            1,  # https://stackoverflow.com/a/10097543
            EMBEDDED_LIB_PATH
        )
        try:
            yield
        finally:
            sys.path = old_sys_path

    @staticmethod
    @contextmanager
    def ignore_exit_code_0():
        """Capture exit calls and ignore those with exit code 0."""
        try:
            yield
        except SystemExit as exit_exc:
            if exit_exc.code != 0:
                raise
