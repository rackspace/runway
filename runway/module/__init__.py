"""Runway module module."""
# (couldn't resist ^)

import logging
import os
import platform
import subprocess
import sys
import json
import hcl
import yaml

from ..util import which

LOGGER = logging.getLogger('runway')
NPM_BIN = 'npm.cmd' if platform.system().lower() == 'windows' else 'npm'
NPX_BIN = 'npx.cmd' if platform.system().lower() == 'windows' else 'npx'


def run_module_command(cmd_list, env_vars):
    """Shell out to provisioner command."""
    try:
        subprocess.check_call(cmd_list, env=env_vars)
    except subprocess.CalledProcessError as shelloutexc:
        sys.exit(shelloutexc.returncode)


class RunwayModule(object):
    """Base class for Runway modules."""

    def __init__(self, context, name, module_folder_name, module_options, environment_options):  # noqa pylint: disable=too-many-arguments
        """Initialize base class."""
        self.context = context
        self.name = name
        self.module_folder_name = module_folder_name
        self.module_options = module_options
        self.environment_options = environment_options

        self.path = RunwayModulePath(module_folder_name)

        # in a later refactoring this loader will not be needed, as the appropriate
        #  environment file(s) will be loaded by the caller instead of by the sub-classes
        self.loader = RunwayModuleEnvironmentFileLoader(self.path)

    def plan(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the plan() method yourself!')

    def deploy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the deploy() method yourself!')

    def destroy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the destroy() method yourself!')


class RunwayModulePath(object):
    """Functions to simplify most of the filesystem access needed by modules."""

    def __init__(self, module_folder_name):
        """Initialize base class."""
        self._module_folder_name = module_folder_name

    def fullpath(self, name):
        """Return the path to the given file from the Runway folder."""
        return os.path.join(self._module_folder_name, name)

    def isfile(self, name):
        """Determine if the given file exist relative to the module."""
        return name and os.path.isfile(self.fullpath(name))

    def isdir(self, name):
        """Determine if the given folder exist relative to the module."""
        return name and os.path.isdir(self.fullpath(name))


class RunwayModuleEnvironmentFileLoader(object):
    """Functions to load environment files from standard places in a module folder."""

    def __init__(self, module_path):
        """Initialize base class."""
        self._module_path = module_path

    def locate_file(self, names):
        """Given a list of filenames, find one that exists (if any) relative to the root."""
        for name in names:
            if self.isfile(name):
                return name
        return None

    def locate_env_file(self, names):
        """Given a list of files, find one that exists (if any) in the root or `env` folders."""
        # first try in the root of the module folder
        location = self._module_path.locate_file(names)
        if not location:
            # next try in the 'env' folder
            env_names = [os.path.join('env', name) for name in names]
            location = self._module_path.locate_file(env_names)
        return location

    def load_hcl_file(self, name):
        """Load the contents of the HCL file into a dict."""
        with open(self._module_path.fullpath(name), 'r') as stream:
            return hcl.load(stream)

    def load_json_file(self, name):
        """Load the contents of the JSON file into a dict."""
        with open(self._module_path.fullpath(name), 'r') as stream:
            return json.load(stream)

    def load_yaml_file(self, name):
        """Load the contents of the YAML file into a dict."""
        with open(self._module_path.fullpath(name), 'r') as stream:
            # load() returns None on an existing but empty file, so provide a default
            return yaml.load(stream) or {}


class NpmHelper(object):
    """Functions to wrap around npm for use by the various modules."""

    def __init__(self, module_name, module_options, env_vars, module_path):
        """Create an instance."""
        self._module_name = module_name
        self._module_options = module_options
        self._env_vars = env_vars
        self._module_path = module_path

    def run_npm_install(self):
        """Run npm install/ci."""
        # Use npm ci if available (npm v5.7+)
        if self._module_options['skip_npm_ci']:
            LOGGER.info("Skipping npm ci or npm install on %s...", self._module_name)
        elif self._env_vars.get('CI') and self._use_npm_ci():
            LOGGER.info("Running npm ci on %s...", self._module_name)
            subprocess.check_call([NPM_BIN, 'ci'])
        else:
            LOGGER.info("Running npm install on %s...", self._module_name)
            subprocess.check_call([NPM_BIN, 'install'])

    def _use_npm_ci(self):
        """Return true if npm ci should be used in lieu of npm install."""
        # https://docs.npmjs.com/cli/ci#description
        with open(os.devnull, 'w') as fnull:
            file_exists = self._module_path.isfile('package-lock.json') or \
                          self._module_path.isfile('npm-shrinkwrap.json')
            if file_exists and subprocess.call([NPM_BIN, 'ci', '-h'],
                                               stdout=fnull,
                                               stderr=subprocess.STDOUT) == 0:
                return True
        return False

    @staticmethod
    def format_npm_command_for_logging(command):
        """Convert npm command list to string for display to user."""
        if platform.system().lower() == 'windows':
            if command[0] == 'npx.cmd' and command[1] == '-c':
                return "npx.cmd -c \"%s\"" % " ".join(command[2:])
            return " ".join(command)
        # Strip out redundant npx quotes not needed when executing the command directly
        return " ".join(command).replace('\'\'', '\'')

    @staticmethod
    def generate_node_command(command, command_opts, path):
        """Return node bin command list for subprocess execution."""
        if which(NPX_BIN):
            # Use npx if available (npm v5.2+)
            LOGGER.debug("Using npx to invoke %s.", command)
            if platform.system().lower() == 'windows':
                cmd_list = [NPX_BIN,
                            '-c',
                            "%s %s" % (command, ' '.join(command_opts))]
            else:
                # The nested app-through-npx-via-subprocess command invocation
                # requires this redundant quoting
                cmd_list = [NPX_BIN,
                            '-c',
                            "''%s %s''" % (command, ' '.join(command_opts))]
        else:
            LOGGER.debug('npx not found; falling back invoking %s shell script '
                         'directly.', command)
            cmd = os.path.join(path, 'node_modules', '.bin', command)
            cmd_list = [cmd] + command_opts
        return cmd_list
