"""runway base module."""
from __future__ import print_function

from contextlib import contextmanager
from subprocess import check_call, check_output

import glob
import logging
import os
import platform
import shutil
import stat
import sys

import yaml

# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from ..embedded.stacker.awscli_yamlhelper import yaml_parse as parse_cloudformation_template  # noqa
from .. import __version__ as version

LOGGER = logging.getLogger('runway')
EMBEDDED_LIB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'embedded'
)


class Base(object):  # noqa pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Base class for deployer classes."""

    def __init__(self, options, env_vars=None, env_root=None,  # noqa pylint: disable=too-many-arguments
                 deploy_opts=None, module_root=None, runway_config_dir=None):
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

        if deploy_opts is None:
            self.deploy_opts = {}
        else:
            self.deploy_opts = deploy_opts

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
        self._environment_name = None

        self.embedded_lib_path = EMBEDDED_LIB_PATH

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

    def get_python_files_at_env_root(self):
        """Return list of python files in env_root."""
        return glob.glob(os.path.join(self.env_root, '*.py'))

    def get_yaml_files_at_env_root(self):
        """Return list of yaml files in env_root."""
        yaml_files = glob.glob(
            os.path.join(self.env_root, '*.yaml')
        )
        yml_files = glob.glob(
            os.path.join(self.env_root, '*.yml')
        )
        return yaml_files + yml_files

    def lint(self, base_dir=None, dirs_to_scan=None):
        """Call code linters."""
        from flake8.main import application as flake8_app
        from yamllint.cli import run as yamllint_run

        if base_dir is None:
            base_dir = self.env_root
        if dirs_to_scan is None:
            dirs_to_scan = self.get_env_dirs()

        if os.path.isfile(os.path.join(base_dir, '.flake8')):
            # config file in env will be picked up automatically
            flake8_config = []
        else:
            # no config file in env; use runway defaults
            flake8_config = [
                ('--append-config=' + os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # noqa
                    'templates',
                    '.flake8'
                ))
            ]
        if os.path.isfile(os.path.join(base_dir, '.yamllint.yml')):
            yamllint_config = os.path.join(base_dir, '.yamllint.yml')
        else:
            yamllint_config = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'templates',
                '.yamllint.yml'
            )
        with self.change_dir(base_dir):
            with self.ignore_exit_code_0():
                LOGGER.info('Starting Flake8 linting...')
                flake8_run = flake8_app.Application()
                flake8_run.run(
                    flake8_config + dirs_to_scan +  self.get_python_files_at_env_root()  # noqa pylint: disable=line-too-long
                )
                flake8_run.exit()
            with self.ignore_exit_code_0():
                LOGGER.info('Flake8 linting complete.')
                LOGGER.info('Starting yamllint...')
                yamllint_run(
                    ["--config-file=%s" % yamllint_config] + dirs_to_scan + self.get_yaml_files_at_env_root()  # noqa pylint: disable=line-too-long
                )
            LOGGER.info('yamllint complete.')

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
                pylint_config = [
                    "--rcfile=%s" % os.path.join(base_dir, '.pylintrc')
                ]
            else:
                # Only reporting on errors ('-E') overrides any ignored errors
                # set in .pylintrc, so it is only being used here when a
                # pylint configuration file is not being used.
                pylint_config = ['-E']

        # Check all python files in repo
        dirs_to_skip = set(['.git',
                            'node_modules',
                            '.serverless'])
        nonblueprint_files = []
        blueprint_files = []
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in dirs_to_skip]
            for name in files:
                filepath = os.path.join(root, name)
                if name[-3:] == '.py' and (
                        root.endswith('blueprints') and
                        not filepath.endswith('__init__.py')):
                    blueprint_files.append(filepath)
                elif name[-3:] == '.py':
                    nonblueprint_files.append(filepath)

        LOGGER.info("Checking python files with pylint (\"No config file "
                    "found...\" messages can be ignored)")
        with self.use_embedded_pkgs():  # for embedded stacker
            with self.ignore_exit_code_0():
                LOGGER.debug("Executing pylint with the following options: \"%s\"",  # noqa
                             ' '.join(pylint_config + nonblueprint_files + blueprint_files))  # noqa pylint: disable=line-too-long
                PylintRun(pylint_config + nonblueprint_files + blueprint_files)
        LOGGER.info('pylint complete.')
        for filepath in blueprint_files:
            # Blueprints should output their template when executed
            self.ensure_file_is_executable(filepath)
            try:
                shell_out_env = os.environ.copy()
                if 'PYTHONPATH' in shell_out_env:
                    shell_out_env['PYTHONPATH'] = (
                        "%s:%s" % (self.embedded_lib_path,
                                   shell_out_env['PYTHONPATH'])
                    )
                else:
                    shell_out_env['PYTHONPATH'] = self.embedded_lib_path
                cfn_template = check_output(
                    [sys.executable, filepath],
                    env=shell_out_env
                )
                if cfn_template == '':
                    raise ValueError('Template output should not be empty!')
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

    def assume_role(self, role_arn, session_name=None, duration_seconds=None,
                    region='us-east-1'):
        """Assume IAM role."""
        import boto3
        if session_name is None:
            session_name = 'runway'
        assume_role_opts = {'RoleArn': role_arn,
                            'RoleSessionName': session_name}
        if duration_seconds:
            assume_role_opts['DurationSeconds'] = int(duration_seconds)
        sts_client = boto3.client('sts', region_name=region)
        LOGGER.info("Assuming role %s...", role_arn)
        response = sts_client.assume_role(**assume_role_opts)
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
            if assume_role_config.get('arn'):
                assume_role_arn = assume_role_config['arn']
                assume_role_duration = assume_role_config.get('duration')
            elif assume_role_config.get(self.environment_name):
                if isinstance(assume_role_config[self.environment_name], dict):
                    assume_role_arn = assume_role_config[self.environment_name]['arn']  # noqa
                    assume_role_duration = assume_role_config[self.environment_name].get('duration')  # noqa pylint: disable=line-too-long
                else:
                    assume_role_arn = assume_role_config[self.environment_name]
                    assume_role_duration = None
            else:
                LOGGER.info('Skipping assume-role; no role found for '
                            'environment %s...',
                            self.environment_name)
                return True

            self.assume_role(
                role_arn=assume_role_arn,
                session_name=assume_role_config.get('session_name', None),
                duration_seconds=assume_role_duration,
                region=region
            )
            return True
        else:
            self.assume_role(role_arn=assume_role_config, region=region)
            return True

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
        for i in ['.terraform-version', 'backend-us-east-1.tfvars',
                  'dev-us-east-1.tfvars', 'main.tf']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'terraform',
                             i),
                os.path.join(module_dir, i),
            )
        LOGGER.info("Sample Terraform app created at %s",
                    module_dir)

    def get_env(self, directory=None):
        """Determine environment name."""
        if self.environment_override_name in self.env_vars:
            return self.env_vars[self.environment_override_name]

        if self.runway_config.get('ignore_git_branch', False):
            LOGGER.info('Skipping environment lookup from current git branch '
                        '("ignore_git_branch" is set to true in the runway '
                        'config)')
        else:
            # These are not located with the top imports because they throw an
            # error if git isn't installed
            from git import Repo as GitRepo
            from git.exc import InvalidGitRepositoryError

            if directory is None:
                directory = self.module_root
            try:
                b_name = GitRepo(
                    directory,
                    search_parent_directories=True
                ).active_branch.name
                LOGGER.info('Deriving environment name from git branch %s...',
                            b_name)
                return self.get_env_from_branch(b_name)
            except InvalidGitRepositoryError:
                pass
        LOGGER.info('Deriving environment name from directory %s...',
                    self.env_root)
        return self.get_env_from_directory(os.path.basename(self.env_root))

    def parse_runway_config(self):
        """Read and parse runway.yml."""
        if not os.path.isfile(self.runway_config_path):
            LOGGER.error("Runway config file was not found (looking for "
                         "%s)",
                         self.runway_config_path)
            sys.exit(1)
        with open(self.runway_config_path) as data_file:
            return yaml.safe_load(data_file)

    def execute(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the execute() method '
                                  'yourself!')

    @property
    def environment_name(self):
        """Return environment name."""
        if not self._environment_name:
            self._environment_name = self.get_env()
        return self._environment_name

    @property
    def runway_config(self):
        """Return parsed runway.yml."""
        if not self._runway_config:
            self._runway_config = self.parse_runway_config()
        return self._runway_config

    @contextmanager
    def use_embedded_pkgs(self):
        """Temporarily prepend embedded packages to sys.path."""
        old_sys_path = list(sys.path)
        sys.path.insert(
            1,  # https://stackoverflow.com/a/10097543
            self.embedded_lib_path
        )
        try:
            yield
        finally:
            sys.path = old_sys_path

    @staticmethod
    def get_env_from_branch(branch_name):
        """Determine environment name from git branch name."""
        if branch_name.startswith('ENV-'):
            return branch_name[4:]
        elif branch_name == 'master':
            LOGGER.info('Translating git branch "master" to environment '
                        '"common"')
            return 'common'
        return branch_name

    @staticmethod
    def get_env_from_directory(directory_name):
        """Determine environment name from directory name."""
        if directory_name.startswith('ENV-'):
            return directory_name[4:]
        return directory_name

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
        if platform.system() != 'Windows' and (
                not stat.S_IXUSR & os.stat(path)[stat.ST_MODE]):
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
    def ignore_exit_code_0():
        """Capture exit calls and ignore those with exit code 0."""
        try:
            yield
        except SystemExit as exit_exc:
            if exit_exc.code != 0:
                raise
