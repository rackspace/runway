"""runway base module."""
from __future__ import print_function

from subprocess import check_call, check_output

import glob
import logging
import os
import shutil
import sys

import yaml

# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from ..embedded.stacker.awscli_yamlhelper import yaml_parse as parse_cloudformation_template  # noqa
from ..util import (
    change_dir, ensure_file_is_executable, get_embedded_lib_path,
    ignore_exit_code_0, use_embedded_pkgs, which
)
from .. import __version__ as version

LOGGER = logging.getLogger('runway')


class Base(object):
    """Base class for deployer classes."""

    def __init__(self, options, env_root=None, runway_config_dir=None):
        """Initialize base class."""
        self.options = options

        if env_root is None:
            self.env_root = os.getcwd()
        else:
            self.env_root = env_root

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

    def get_env_dirs(self):
        """Return list of directories in env_root."""
        repo_dirs = next(os.walk(self.env_root))[1]
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
        with change_dir(base_dir):
            with ignore_exit_code_0():
                LOGGER.info('Starting Flake8 linting...')
                flake8_run = flake8_app.Application()
                flake8_run.run(
                    flake8_config + dirs_to_scan +  self.get_python_files_at_env_root()  # noqa pylint: disable=line-too-long
                )
                flake8_run.exit()
            with ignore_exit_code_0():
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
            if which('foodcritic') is None or which('cookstyle') is None:
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

        if nonblueprint_files + blueprint_files:
            LOGGER.info("Checking python files with pylint (\"No config file "
                        "found...\" messages can be ignored)")
            with use_embedded_pkgs():  # for embedded stacker
                with ignore_exit_code_0():
                    LOGGER.debug("Executing pylint with the following options: \"%s\"",  # noqa
                                 ' '.join(pylint_config + nonblueprint_files + blueprint_files))  # noqa pylint: disable=line-too-long
                    PylintRun(pylint_config + nonblueprint_files + blueprint_files)  # noqa
            LOGGER.info('pylint complete.')
            for filepath in blueprint_files:
                # Blueprints should output their template when executed
                ensure_file_is_executable(filepath)
                try:
                    shell_out_env = os.environ.copy()
                    if 'PYTHONPATH' in shell_out_env:
                        shell_out_env['PYTHONPATH'] = (
                            "%s:%s" % (get_embedded_lib_path(),
                                       shell_out_env['PYTHONPATH'])
                        )
                    else:
                        shell_out_env['PYTHONPATH'] = get_embedded_lib_path()
                    cfn_template = check_output(
                        [sys.executable, filepath],
                        env=shell_out_env
                    ).decode()
                    if not cfn_template:
                        raise ValueError('Template output should not be empty!')  # noqa
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

    def path_only_contains_dirs(self, path):
        """Return boolean on whether a path only contains directories."""
        pathlistdir = os.listdir(path)
        if pathlistdir == []:
            return True
        if any(os.path.isfile(os.path.join(path, i)) for i in pathlistdir):
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
            module_dir = os.path.join(self.env_root,
                                      'runway-sample-tfstate.cfn')
        self.generate_sample_module(module_dir)
        for i in ['stacks.yaml', 'dev-us-east-1.env']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'stacker',
                             i),
                os.path.join(module_dir, i)
            )
        os.mkdir(os.path.join(module_dir, 'tfstate_blueprints'))
        for i in ['__init__.py', 'tf_state.py']:
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'templates',
                             'stacker',
                             'tfstate_blueprints',
                             i),
                os.path.join(module_dir, 'tfstate_blueprints', i)
            )
        os.chmod(  # make blueprint executable
            os.path.join(module_dir, 'tfstate_blueprints', 'tf_state.py'),
            os.stat(os.path.join(module_dir,
                                 'tfstate_blueprints',
                                 'tf_state.py')).st_mode | 0o0111
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

    def parse_runway_config(self):
        """Read and parse runway.yml."""
        if not os.path.isfile(self.runway_config_path):
            LOGGER.error("Runway config file was not found (looking for "
                         "%s)",
                         self.runway_config_path)
            sys.exit(1)
        with open(self.runway_config_path) as data_file:
            return yaml.safe_load(data_file)

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
    def generate_sample_module(module_dir):
        """Generate skeleton sample module."""
        if os.path.isdir(module_dir):
            LOGGER.error("Error generating sample module -- directory %s "
                         "already exists!",
                         module_dir)
            sys.exit(1)
        os.mkdir(module_dir)
