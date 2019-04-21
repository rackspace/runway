"""Runway module module."""
# (couldn't resist ^)

import logging
import os
import platform
import subprocess
import sys

from ..util import which

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


def run_module_command(cmd_list, env_vars, exit_on_error=True):
    """Shell out to provisioner command."""
    if exit_on_error:
        try:
            subprocess.check_call(cmd_list, env=env_vars)
        except subprocess.CalledProcessError as shelloutexc:
            sys.exit(shelloutexc.returncode)
    else:
        subprocess.check_call(cmd_list, env=env_vars)


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


def warn_on_boto_env_vars(env_vars):
    """Inform user if boto-specific environment variables are in use."""
    # https://github.com/serverless/serverless/issues/2151#issuecomment-255646512
    if env_vars.get('AWS_DEFAULT_PROFILE') and not (
            env_vars.get('AWS_PROFILE')):
        LOGGER.warning('AWS_DEFAULT_PROFILE environment variable is set '
                       'during use of nodejs-based module and AWS_PROFILE is '
                       'not set -- you likely want to set AWS_PROFILE instead')


class RunwayModule(object):
    """Base class for Runway modules."""

    def __init__(self, context, path, options=None):
        """Initialize base class."""
        self.context = context

        self.path = path

        if options is None:
            self.options = {}
        else:
            self.options = options

    # the rest of these 'abstract' methods must have names which match
    #  the commands defined in `cli.py`

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
