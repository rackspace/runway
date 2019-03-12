"""Cloudformation module."""

import logging
import os
import platform
import re
import sys
import yaml

from . import RunwayModule, run_module_command
from ..util import change_dir, get_embedded_lib_path

LOGGER = logging.getLogger('runway')


def make_stacker_cmd_string(args, lib_path):
    """Generate stacker invocation script from command line arg list.

    This is the standard stacker invocation script, with the following changes:
    * Adding our explicit arguments to parse_args (instead of leaving it empty)
    * Overriding sys.argv
    * Adding embedded runway lib directory to sys.path
    """
    if platform.system().lower() == 'windows':
        # Because this will be run via subprocess, the backslashes on Windows
        # will cause command errors
        lib_path = lib_path.replace('\\', '/')
    return ("import sys;"
            "sys.argv = ['stacker'] + {args};"
            "sys.path.insert(1, '{lib_path}');"
            "from stacker.logger import setup_logging;"
            "from stacker.commands import Stacker;"
            "stacker = Stacker(setup_logging=setup_logging);"
            "args = stacker.parse_args({args});"
            "stacker.configure(args);args.run(args)".format(args=str(args),
                                                            lib_path=lib_path))


class CloudFormation(RunwayModule):
    """CloudFormation (Stacker) Runway Module."""

    def gen_stacker_env_files(self):
        """Generate possible Stacker environment filenames."""
        return [
            # Give preference to explicit environment-region files
            "%s-%s.env" % (self.context.env_name, self.context.env_region),
            # Fallback to environment name only
            "%s.env" % self.context.env_name
        ]

    def get_stacker_env_file(self):
        """Determine Stacker environment file name."""
        return self.folder.locate_file(self.gen_stacker_env_files())

    def ensure_stacker_compat_config(self, config_filename):
        """Ensure config file can be loaded by Stacker."""
        try:
            self.folder.load_yaml_file(config_filename)
        except yaml.constructor.ConstructorError as yaml_error:
            if yaml_error.problem.startswith(
                    'could not determine a constructor for the tag \'!'):
                LOGGER.error('"%s" appears to be a CloudFormation template, '
                             'but is located in the top level of a module '
                             'alongside the CloudFormation config files (i.e. '
                             'the file or files indicating the stack names & '
                             'parameters). Please move the template to a '
                             'subdirectory.',
                             config_filename)
                sys.exit(1)

    def run_stacker(self, command='diff'):  # pylint: disable=too-many-branches
        """Run Stacker."""
        response = {'skipped_configs': False}
        stacker_cmd = [command, "--region=%s" % self.context.env_region]

        if command == 'destroy':
            stacker_cmd.append('--force')
        elif command == 'build':
            if 'CI' in self.context.env_vars:
                stacker_cmd.append('--recreate-failed')
            else:
                stacker_cmd.append('--interactive')

        if 'DEBUG' in self.context.env_vars:
            stacker_cmd.append('--verbose')  # Increase logging if requested

        stacker_env_file = self.get_stacker_env_file()

        if self.environment:
            for (key, val) in self.environment.items():
                stacker_cmd.extend(['-e', "%s=%s" % (key, val)])
        if stacker_env_file:
            stacker_cmd.append(stacker_env_file)

        with change_dir(self.path):
            # Iterate through any stacker yaml configs to deploy them in order
            # or destroy them in reverse order
            for _root, _dirs, files in os.walk(self.path):
                for name in (
                        reversed(sorted(files))
                        if command == 'destroy'
                        else sorted(files)):
                    if re.match(r"runway(\..*)?\.yml", name) or (
                            name.startswith('.')):
                        # Hidden files (e.g. .gitlab-ci.yml) or runway configs
                        # definitely aren't stacker config files
                        continue
                    if os.path.splitext(name)[1] in ['.yaml', '.yml']:
                        if not (stacker_env_file or self.environment):
                            response['skipped_configs'] = True
                            LOGGER.info(
                                "Skipping stacker %s of %s; no environment "
                                "file found for this environment/region "
                                "(looking for one of \"%s\")",
                                command,
                                name,
                                ', '.join(self.gen_stacker_env_files()))
                            continue
                        self.ensure_stacker_compat_config(name)
                        LOGGER.info("Running stacker %s on %s in region %s",
                                    command,
                                    name,
                                    self.context.env_region)
                        stacker_cmd_str = make_stacker_cmd_string(
                            stacker_cmd + [name],
                            get_embedded_lib_path()
                        )
                        stacker_cmd_list = [sys.executable, '-c']
                        LOGGER.debug(
                            "Stacker command being executed: %s \"%s\"",
                            ' '.join(stacker_cmd_list),
                            stacker_cmd_str
                        )
                        run_module_command(
                            cmd_list=stacker_cmd_list + [stacker_cmd_str],
                            env_vars=self.context.env_vars
                        )
                break  # only need top level files
        return response

    def plan(self):
        """Run stacker diff."""
        self.run_stacker(command='diff')

    def deploy(self):
        """Run stacker build."""
        self.run_stacker(command='build')

    def destroy(self):
        """Run stacker destroy."""
        self.run_stacker(command='destroy')
