"""``runway dismantle`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options
from ._destroy import destroy

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("dismantle", short_help="alias of destroy")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def dismantle(ctx: click.Context, **kwargs: Any) -> None:
    """Alias of "runway destroy".

    For more information, refer to the output of "runway destroy --help".

    """
    LOGGER.verbose("forwarding to destroy...")
    ctx.forward(destroy, **kwargs)
