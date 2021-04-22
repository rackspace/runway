"""``runway taxi`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options
from ._plan import plan

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("taxi", short_help="alias of plan")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def taxi(ctx: click.Context, **kwargs: Any) -> None:
    """Alias of "runway plan".

    For more information, refer to the output of "runway plan --help".

    """
    LOGGER.verbose("forwarding to plan...")
    ctx.forward(plan, **kwargs)
