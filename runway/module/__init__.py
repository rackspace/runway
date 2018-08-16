"""Runway module module."""
# (couldn't resist ^)

import logging
import subprocess
import sys

LOGGER = logging.getLogger('runway')


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
