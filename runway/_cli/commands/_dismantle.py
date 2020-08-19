"""``runway dismantle`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any  # pylint: disable=W

import click

from .. import options
from ._destroy import destroy

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("dismantle", short_help="alias of destroy")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def dismantle(ctx, **kwargs):
    # type: (click.Context, Any) -> None
    """Alias of "runway destroy"."""
    LOGGER.verbose("forwarding to destroy...")
    ctx.forward(destroy, **kwargs)
