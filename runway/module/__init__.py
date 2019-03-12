"""Runway module module."""
# (couldn't resist ^)

import logging
import os
import platform
import subprocess
import sys
import json
import yaml

from ..util import which, better_dict_get

LOGGER = logging.getLogger('runway')
NPM_BIN = 'npm.cmd' if platform.system().lower() == 'windows' else 'npm'
NPX_BIN = 'npx.cmd' if platform.system().lower() == 'windows' else 'npx'


def run_module_command(cmd_list, env_vars):
    """Shell out to provisioner command."""
    try:
        subprocess.check_call(cmd_list, env=env_vars)
    except subprocess.CalledProcessError as shelloutexc:
        sys.exit(shelloutexc.returncode)


class RunwayModule(object):  # noqa pylint: disable=too-many-instance-attributes
    """Base class for Runway modules."""

    def __init__(self, context, path, runway_file_options=None):
        """Initialize base class."""
        self.name = os.path.basename(path)

        self.context = context

        self.folder = RunwayModuleFolder(path)

        # it would be good to remove the need for sub-classes to refer
        #  to this directly, and have them rely on 'folder' instead
        self.path = path

        environments_options = better_dict_get(runway_file_options, 'environments', {})
        self.environment_options = environments_options.get(context.env_name)
        if self.environment_options is not None:
            # it will almost always be a 'dict', but some modules (like serverless) support
            #  a boolean, which indicates we want the module, and we have no values to set
            if isinstance(self.environment_options, bool):
                if self.environment_options:
                    self.environment_options = {}
                else:
                    self.environment_options = None

        self.module_options = better_dict_get(runway_file_options, 'options', {})

        # should global options be in the context instead?
        self.project_options = {}
        self.project_options['skip_npm_ci'] = runway_file_options.get('skip_npm_ci')

        self.npm = NpmHelper(self.name, self.project_options, self.context.env_vars, self.folder)

        # ideally we don't need this, but there are extreme situations (like creating
        #  a Cloudformation module inside the StaticSite module) that are currently
        #  very hard without access to this
        self._runway_file_options = runway_file_options

    def plan(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the plan() method yourself!')

    def deploy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the deploy() method yourself!')

    def destroy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the destroy() method yourself!')


class RunwayModuleFolder(object):
    """Functions to manage filesystem access in a module folder."""

    def __init__(self, path):
        """Initialize base class."""
        self._path = path

    def fullpath(self, name):
        """Return the absolute path to the given file."""
        return os.path.join(self._path, name)

    def isfile(self, name):
        """Determine if the given file exist relative to the module."""
        return name and os.path.isfile(self.fullpath(name))

    def isdir(self, name):
        """Determine if the given folder exist relative to the module."""
        return name and os.path.isdir(self.fullpath(name))

    def locate_file(self, names):
        """Given a list of files, find one that exists (if any) in the root folder."""
        for name in names:
            if self.isfile(name):
                return name
        return None

    def locate_env_file(self, names):
        """Given a list of files, find one that exists (if any) in the root or `env` folders."""
        # first try in the root of the module folder
        location = self.locate_file(names)
        if not location:
            # next try in the 'env' folder
            env_names = [os.path.join('env', name) for name in names]
            location = self.locate_file(env_names)
        return location

    def load_json_file(self, name):
        """Load the contents of the JSON file into a dict."""
        with open(self.fullpath(name), 'r') as stream:
            return json.load(stream)

    def load_yaml_file(self, name):
        """Load the contents of the YAML file into a dict."""
        with open(self.fullpath(name), 'r') as stream:
            # load() returns None on an existing but empty file, so provide a default
            return yaml.load(stream) or {}


class NpmHelper(object):
    """Functions to wrap around npm for use by the various modules."""

    def __init__(self, module_name, project_options, env_vars, folder):
        """Create an instance."""
        self._module_name = module_name
        self._project_options = project_options
        self._env_vars = env_vars
        self._folder = folder

    def run_npm_install(self):
        """Run npm install/ci."""
        # Use npm ci if available (npm v5.7+)
        if self._project_options['skip_npm_ci']:
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
            file_exists = self._folder.isfile('package-lock.json') or \
                          self._folder.isfile('npm-shrinkwrap.json')
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
