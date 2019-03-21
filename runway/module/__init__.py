"""Runway module module."""
# (couldn't resist ^)

import logging
import os
import platform
import subprocess
import sys
import json
import yaml

from ..util import which, better_dict_get, merge_dicts

LOGGER = logging.getLogger('runway')
NPM_BIN = 'npm.cmd' if platform.system().lower() == 'windows' else 'npm'
NPX_BIN = 'npx.cmd' if platform.system().lower() == 'windows' else 'npx'


def format_npm_command_for_logging(command):
    """Convert npm command list to string for display to user."""
    if platform.system().lower() == 'windows':
        if command[0] == 'npx.cmd' and command[1] == '-c':
            return "npx.cmd -c \"%s\"" % " ".join(command[2:])
        return " ".join(command)
    # Strip out redundant npx quotes not needed when executing the command
    # directly
    return " ".join(command).replace('\'\'', '\'')


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
        cmd_list = [
            os.path.join(path,
                         'node_modules',
                         '.bin',
                         command)
        ] + command_opts
    return cmd_list


def run_module_command(cmd_list, env_vars):
    """Shell out to provisioner command."""
    try:
        subprocess.check_call(cmd_list, env=env_vars)
    except subprocess.CalledProcessError as shelloutexc:
        sys.exit(shelloutexc.returncode)


def use_npm_ci(path):
    """Return true if npm ci should be used in lieu of npm install."""
    # https://docs.npmjs.com/cli/ci#description
    with open(os.devnull, 'w') as fnull:
        if ((os.path.isfile(os.path.join(path,
                                         'package-lock.json')) or
             os.path.isfile(os.path.join(path,
                                         'npm-shrinkwrap.json'))) and
                subprocess.call(
                    [NPM_BIN, 'ci', '-h'],
                    stdout=fnull,
                    stderr=subprocess.STDOUT
                ) == 0):
            return True
    return False


def run_npm_install(path, options, context):
    """Run npm install/ci."""
    # Use npm ci if available (npm v5.7+)
    if options.get('skip_npm_ci'):
        LOGGER.info("Skipping npm ci or npm install on %s...",
                    os.path.basename(path))
    elif context.env_vars.get('CI') and use_npm_ci(path):  # noqa
        LOGGER.info("Running npm ci on %s...",
                    os.path.basename(path))
        subprocess.check_call([NPM_BIN, 'ci'])
    else:
        LOGGER.info("Running npm install on %s...",
                    os.path.basename(path))
        subprocess.check_call([NPM_BIN, 'install'])


class RunwayModule(object):
    """Base class for Runway modules."""

    def __init__(self, context, path, options=None):
        """Initialize base class."""
        self.name = os.path.basename(path)

        self.context = context

        # it would be good to remove the need for sub-classes to refer
        #  to this directly, and have them rely on 'folder' instead
        self.path = path

        self.folder = RunwayModuleFolder(path)

        # FUTURE: break out the pieces we actually care about, rather passing the whole dict along
        if options is None:
            self.options = {}
        else:
            self.options = options

        # while the environment config is indeed part of 'options', we can save ourselves
        #  work later by pulling the environment-specific parts out here
        all_environments_node = better_dict_get(self.options, 'environments', {})
        self.environment_config = all_environments_node.get(context.env_name)

        # `dev: True` is valid in `runway.yml` but we need it to be a dict
        if self.environment_config and isinstance(self.environment_config, bool):
            self.environment_config = {}

        # we might have some shared values to combine with the values specific to this environment
        shared_config = all_environments_node.get("*")
        if shared_config:
            if self.environment_config:
                self.environment_config = merge_dicts(shared_config, self.environment_config)
            else:
                self.environment_config = shared_config

    def plan(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the plan() method '
                                  'yourself!')

    def deploy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the deploy() method '
                                  'yourself!')

    def destroy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the destroy() method '
                                  'yourself!')


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
        return os.path.isfile(self.fullpath(name))

    def isdir(self, name):
        """Determine if the given folder exist relative to the module."""
        return os.path.isdir(self.fullpath(name))

    def locate_file(self, names):
        """Given a list of files, find one that exists (if any) in the root folder."""
        for name in names:
            if self.isfile(name):
                return name
        # IDEA: it might be better to find *all* of the existing files,
        #  and log a warning if more than one is found?
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
