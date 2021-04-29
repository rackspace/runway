"""``runway preflight`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import TYPE_CHECKING, Any, cast

import click

from .. import options
from ._test import test

if TYPE_CHECKING:
    from ..._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("preflight", short_help="alias of test")
@options.debug
@options.deploy_environment
@options.no_color
@options.verbose
@click.pass_context
def preflight(ctx: click.Context, **kwargs: Any) -> None:
    """Alias of "runway test".

    For more information, refer to the output of "runway test --help".

    """
    LOGGER.verbose("forwarding to test...")
    ctx.forward(test, **kwargs)
