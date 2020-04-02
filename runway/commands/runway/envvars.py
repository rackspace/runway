"""Output ``runway.yml``-defined environment variables.

OS environment variables can be set in ``runway.yml`` for different
Runway environments (e.g. dev & prod ``KUBECONFIG`` values). The
``envvars`` command allows access to these values for use outside of
Runway.

Example:
  .. code-block:: shell

    $ eval "$(runway envvars)"

"""
from __future__ import print_function

import logging
import os
import platform
import sys
from typing import Dict  # noqa pylint: disable=unused-import

from ...context import Context
from ...util import merge_dicts, merge_nested_environment_dicts
from ..runway_command import RunwayCommand, get_env

LOGGER = logging.getLogger('runway')


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
        if self.runway_config.deployments:
            context = Context(
                env_name=get_env(self.env_root,
                                 self.runway_config.ignore_git_branch),
                env_region=None,
                env_root=self.env_root,
                env_vars=os.environ.copy()
            )
            env_vars = {}
            for deployment in self.runway_config.deployments:
                deployment.resolve(context, self.runway_vars)
                env_vars = merge_dicts(env_vars, deployment.env_vars)
            if env_vars:
                env_vars = merge_nested_environment_dicts(
                    env_vars,
                    env_name=context.env_name,
                    env_root=context.env_root
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
            print('ERROR: no runway deployments found', file=sys.stderr)
            sys.exit(1)
