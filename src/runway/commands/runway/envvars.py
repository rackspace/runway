"""The envvars command."""
from __future__ import print_function
from typing import Dict  # noqa pylint: disable=unused-import
import logging
import os
import platform
import sys

from ..runway_command import RunwayCommand, get_env
from ...util import merge_dicts, merge_nested_environment_dicts

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
        """Output runway-defined environment variables."""
        if self.runway_config.get('deployments'):
            env_vars = {}
            for i in self.runway_config.get('deployments'):
                env_vars = merge_dicts(env_vars, i.get('env_vars', {}))
            if env_vars:
                env_vars = merge_nested_environment_dicts(
                    env_vars,
                    env_name=get_env(
                        os.getcwd(),
                        ignore_git_branch=self.runway_config.get('ignore_git_branch'),
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
            print('ERROR: no runway deployments found', file=sys.stderr)
            sys.exit(1)
