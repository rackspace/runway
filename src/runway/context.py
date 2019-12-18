"""Runway context module."""
import logging
import os


LOGGER = logging.getLogger('runway')


def echo_detected_environment(env_name, env_vars):
    """Print a helper note about how the environment was determined."""
    env_override_name = 'DEPLOY_ENVIRONMENT'
    LOGGER.info("")
    if env_override_name in env_vars:
        LOGGER.info("Environment \"%s\" was determined from the %s environment variable.",
                    env_name,
                    env_override_name)
        LOGGER.info("If this is not correct, update "
                    "the value (or unset it to fall back to the name of "
                    "the current git branch or parent directory).")
    else:
        LOGGER.info("Environment \"%s\" was determined from the current "
                    "git branch or parent directory.",
                    env_name)
        LOGGER.info("If this is not the environment name, update the branch/folder name or "
                    "set an override value via the %s environment variable",
                    env_override_name)
    LOGGER.info("")


class Context(object):
    """Runway execution context."""

    env_override_name = 'DEPLOY_ENVIRONMENT'

    def __init__(self, env_name,  # pylint: disable=too-many-arguments
                 env_region, env_root, env_vars=None,
                 command=None):
        """Initialize base class."""
        self.env_name = env_name
        self.env_region = env_region
        self.env_root = env_root
        self.command = command
        self.env_vars = env_vars or os.environ.copy()
        self._env_name_from_env = bool(self.env_vars.get(self.env_override_name))

        self.echo_detected_environment()

        if not self._env_name_from_env:
            self.env_vars.update({'DEPLOY_ENVIRONMENT': self.env_name})

    def echo_detected_environment(self):
        """Print a helper note about how the environment was determined."""
        LOGGER.info("")
        if self._env_name_from_env:
            LOGGER.info("Environment \"%s\" was determined from the %s "
                        "environment variable.", self.env_name,
                        self.env_override_name)
            LOGGER.info("If this is not correct, update "
                        "the value (or unset it to fall back to the name of "
                        "the current git branch or parent directory).")
        else:
            LOGGER.info("Environment \"%s\" was determined from the current "
                        "git branch or parent directory.",
                        self.env_name)
            LOGGER.info("If this is not the environment name, update the "
                        "branch/folder name or set an override value via "
                        "the %s environment variable", self.env_override_name)
        LOGGER.info("")

    def save_existing_iam_env_vars(self):
        """Backup IAM environment variables for later restoration."""
        for i in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                  'AWS_SESSION_TOKEN']:
            if i in self.env_vars:
                self.env_vars['OLD_' + i] = self.env_vars[i]

    def restore_existing_iam_env_vars(self):
        """Restore backed up IAM environment variables."""
        for i in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                  'AWS_SESSION_TOKEN']:
            if 'OLD_' + i in self.env_vars:
                self.env_vars[i] = self.env_vars['OLD_' + i]
            elif i in self.env_vars:
                self.env_vars.pop(i)
