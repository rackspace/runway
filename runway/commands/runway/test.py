"""The test command."""

import logging
import os
import sys

from subprocess import check_call, check_output
from subprocess import CalledProcessError

# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from runway.embedded.stacker.awscli_yamlhelper \
    import yaml_parse as parse_cloudformation_template  # noqa
from runway.util import (
    change_dir, get_embedded_lib_path, ignore_exit_code_0, use_embedded_pkgs,
    which
)

from ..runway_command import RunwayCommand

LOGGER = logging.getLogger('runway')


class Test(RunwayCommand):
    """Extend RunwayCommand with execute to run the test method."""

    def execute(self):
        """Execute tests."""
        self.lint()
        self.cookbook_tests()
        self.python_tests()
        self.cfn_lint()

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
        if os.path.isfile(os.path.join(base_dir, '.yamllint')):
            yamllint_config = os.path.join(base_dir, '.yamllint')
        elif os.path.isfile(os.path.join(base_dir, '.yamllint.yml')):
            yamllint_config = os.path.join(base_dir, '.yamllint.yml')
        else:
            yamllint_config = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
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
        from pylint.lint import Run

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
                    Run(pylint_config + nonblueprint_files + blueprint_files)  # noqa
            LOGGER.info('pylint complete.')
            for filepath in blueprint_files:
                try:
                    shell_out_env = os.environ.copy()
                    if 'PYTHONPATH' in shell_out_env:
                        shell_out_env['PYTHONPATH'] = ("%s:%s" % (get_embedded_lib_path(),
                                                                  shell_out_env['PYTHONPATH']))
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

    def cfn_lint(self):
        """Run cfn-lint on templates."""
        if os.path.isfile(os.path.join(self.env_root,
                                       '.cfnlintrc')):
            LOGGER.info('Starting cfn-lint checks...')
            try:
                check_call([sys.executable,
                            '-c',
                            "import sys;from cfnlint.__main__ import main;sys.argv = ['cfn-lint'];sys.exit(main())"])  # noqa pylint: disable=line-too-long
            except CalledProcessError:
                sys.exit(1)
            LOGGER.info('cfn-lint complete')
        else:
            LOGGER.debug('Skipping cfn-lint checks (no .cfnlintrc file '
                         'defined)')
