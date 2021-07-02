"""``runway plan`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
import os
import platform
from typing import TYPE_CHECKING, Any, Dict, cast

import click
from pydantic import ValidationError

from ...core import Runway
from ...exceptions import ConfigNotFound, VariablesFileNotFound
from .. import options

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("envvars", short_help="exportable env_vars")
@options.debug
@options.deploy_environment
@options.no_color
@options.verbose
@click.pass_context
def envvars(ctx: click.Context, debug: bool, **_: Any) -> None:
    """Output "env_vars" defined in the Runway config file.

    OS environment variables can be set in the Runway config file for different
    Runway environments (e.g. dev & prod KUBECONFIG values).
    This command allows access to these values for use outside of Runway.

    NOTE: Only outputs "env_vars" defined in deployments, not modules.

    """
    if not (ctx.obj.debug or ctx.obj.verbose):
        logging.getLogger("runway").setLevel(logging.ERROR)  # suppress warnings

    ctx.obj.env.ci = True
    LOGGER.verbose("forced Runway to non-interactive mode to suppress prompts")
    try:
        env_vars = Runway(
            ctx.obj.runway_config, ctx.obj.get_runway_context()
        ).get_env_vars()
    except ValidationError as err:
        LOGGER.error(err, exc_info=debug)
        ctx.exit(1)
    except (ConfigNotFound, VariablesFileNotFound) as err:
        LOGGER.error(err.message, exc_info=debug)
        ctx.exit(1)

    if not env_vars:
        LOGGER.error("No env_vars defined in %s", ctx.obj.runway_config_path)
        ctx.exit(1)
    LOGGER.debug("env_vars: %s", env_vars)
    print_env_vars(env_vars)


def print_env_vars(env_vars: Dict[str, Any]) -> None:
    """Print environment variables."""
    if platform.system() == "Windows":
        if os.getenv("MSYSTEM", "").startswith("MINGW"):
            return __print_env_vars_posix(env_vars)  # git bash
        return __print_env_vars_psh(env_vars)
    return __print_env_vars_posix(env_vars)


def __print_env_vars_posix(env_vars: Dict[str, Any]) -> None:
    """Print environment variables for bash."""
    LOGGER.debug("using posix formating for environment variable export")
    for key, val in env_vars.items():
        click.echo(f'export {key}="{val}"')


def __print_env_vars_psh(env_vars: Dict[str, Any]) -> None:
    """Print environment variables for Powershell."""
    LOGGER.debug("using powershell formating for environment variable export")
    for key, val in env_vars.items():
        click.echo(f'$env:{key} = "{val}"')
