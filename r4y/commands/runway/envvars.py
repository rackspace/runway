"""Output ``r4y.yml``-defined environment variables.

OS environment variables can be set in ``r4y.yml`` for different
Runway environments (e.g. dev & prod ``KUBECONFIG`` values). The
``envvars`` command allows access to these values for use outside of
Runway.

Example:
  .. code-block:: shell

    $ eval "$(r4y envvars)"

"""
from __future__ import print_function
from typing import Dict  # noqa pylint: disable=unused-import
import logging
import os
import platform
import sys

from ..r4y_command import RunwayCommand, get_env
from ...util import merge_dicts, merge_nested_environment_dicts

LOGGER = logging.getLogger('r4y')


def print_env_vars_psh(env_vars):
    # type: (Dict[str, str]) -> None
    """Print environment variables for Powershell."""
    for (key, val) in env_vars.items():
        print("$env:%s =\"%s\"" % (key, val))


def print_env_vars_posix(env_vars):
    # type: (Dict[str, str]) -> None
    """Print environment variables for bash."""
    for (key, val) in env_vars.items():
        print("export %s=\"%s\"" % (key, val))


class EnvVars(RunwayCommand):
    """Extend RunwayCommand with execution of envvars."""

    def execute(self):
        """Output Runway-defined environment variables."""
        if self.r4y_config.get('deployments'):
            env_vars = {}
            for i in self.r4y_config.get('deployments'):
                env_vars = merge_dicts(env_vars, i.get('env_vars', {}))
            if env_vars:
                env_vars = merge_nested_environment_dicts(
                    env_vars,
                    env_name=get_env(
                        os.getcwd(),
                        ignore_git_branch=self.r4y_config.get('ignore_git_branch'),
                    ),
                    env_root=os.getcwd()
                )

            if 'MSYSTEM' in os.environ and (
                    os.environ['MSYSTEM'].startswith('MINGW') and (
                        platform.system() == 'Windows')):  # type: ignore
                print_env_vars_posix(env_vars)  # git bash
            elif platform.system() == 'Windows':  # type: ignore
                print_env_vars_psh(env_vars)
            else:
                print_env_vars_posix(env_vars)
        else:
            print('ERROR: no r4y deployments found', file=sys.stderr)
            sys.exit(1)
