"""``runway gen-sample stacker`` command."""
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from ._cfngin import cfngin

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("stacker", short_help="deprecated, use cfngin")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def stacker(ctx: click.Context, **kwargs: Any) -> None:
    """[DEPRECATED] Generate a sample CFNgin project using Blueprints."""  # noqa
    LOGGER.warning(
        "This command has been deprecated and will be removed in "
        "the next major release."
    )
    LOGGER.verbose("forwarding to cfngin...")
    ctx.forward(cfngin, **kwargs)
