"""``runway takeoff`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options
from ._deploy import deploy

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("takeoff", short_help="alias of deploy")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def takeoff(ctx: click.Context, **kwargs: Any) -> None:
    """Alias of "runway deploy".

    For more information, refer to the output of "runway deploy --help".

    """
    LOGGER.verbose("forwarding to deploy...")
    ctx.forward(deploy, **kwargs)
