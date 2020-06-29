"""``runway plan`` command."""
import logging
import os
import platform
from typing import Any, Dict  # pylint: disable=W

import click

from ...core import Runway
from .. import options

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('envvars')
@options.debug
@options.deploy_environment
@click.pass_context
def envvars(ctx, **_):
    """Output env_vars defined in the Runway config file.

    OS environment variables can be set in Runway config file for different
    Runway environments (e.g. dev & prod KUBECONFIG values).
    This command allows access to these values for use outside of Runway.

    NOTE: Only outputs env_vars defined in deployments, not modules.

    """
    if not ctx.obj.debug:
        logging.getLogger('runway').setLevel(logging.ERROR)  # suppress warnings
    ctx.obj.env.ci = True  # suppress any prompts
    env_vars = Runway(ctx.obj.runway_config,
                      ctx.obj.get_runway_context()).get_env_vars()

    if not env_vars:
        LOGGER.error('No env_vars defined in %s', ctx.obj.runway_config_path)
        ctx.exit(1)
    LOGGER.debug('printing env_vars: %s', env_vars)
    print_env_vars(env_vars)


def print_env_vars(env_vars):
    # type: (Dict[str, Any]) -> None
    """Print environment variables."""
    if platform.system() == 'Windows':
        if os.getenv('MSYSTEM', '').startswith('MINGW'):
            return __print_env_vars_posix(env_vars)  # git bash
        return __print_env_vars_psh(env_vars)
    return __print_env_vars_posix(env_vars)


def __print_env_vars_posix(env_vars):
    # type: (Dict[str, Any]) -> None
    """Print environment variables for bash."""
    LOGGER.debug('using posix formating for environment variable export')
    for key, val in env_vars.items():
        click.echo('export {}="{}"'.format(key, val))


def __print_env_vars_psh(env_vars):
    # type: (Dict[str, Any]) -> None
    """Print environment variables for Powershell."""
    LOGGER.debug('using powershell formating for environment variable export')
    for key, val in env_vars.items():
        click.echo('$env:{} = "{}"'.format(key, val))
