"""Runway module module."""
# (couldn't resist ^)

import logging
import os
import subprocess
import sys

from ..util import which

LOGGER = logging.getLogger('runway')


def format_npm_command_for_logging(command):
    """Convert npm command list to string for display to user."""
    # Strip out redundant npx quotes not needed when executing the command
    # directly
    return " ".join(command).replace('\'\'', '\'')


def generate_node_command(command, command_opts, path):
    """Return node bin command list for subprocess execution."""
    if which('npx'):
        # Use npx if available (npm v5.2+)
        LOGGER.debug("Using npx to invoke %s.", command)
        # The nested cdk-through-npx-via-subprocess command invocation
        # requires this redundant quoting
        cmd_list = ['npx',
                    '-c',
                    "''%s %s''" % (command, ' '.join(command_opts))]
    else:
        LOGGER.debug('npx not found; falling back invoking %s shell script '
                     'script directly.', command)
        cmd_list = [
            os.path.join(path,
                         'node_modules',
                         '.bin',
                         command)
        ] + command_opts
    return cmd_list


def warn_on_skipped_configs(result, env_name, env_vars):
    """Print a helper note about how the environment was determined."""
    env_override_name = 'DEPLOY_ENVIRONMENT'
    if ('skipped_configs' in result and
            result['skipped_configs']):
        if env_override_name in env_vars:
            LOGGER.info("Environment \"%s\" was determined from the %s "
                        "environment variable. If this is not correct, update "
                        "the value (or unset it to fall back to the name of "
                        "the current git branch or parent directory).",
                        env_name,
                        env_override_name)
        else:
            LOGGER.info("Environment \"%s\" was determined from the current "
                        "git branch or parent directory. If this is not the "
                        "environment name, update the branch/folder name or "
                        "set an override value via the %s environment "
                        "variable",
                        env_name,
                        env_override_name)


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
                    ['npm', 'ci', '-h'],
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
        subprocess.check_call(['npm', 'ci'])
    else:
        LOGGER.info("Running npm install on %s...",
                    os.path.basename(path))
        subprocess.check_call(['npm', 'install'])


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
