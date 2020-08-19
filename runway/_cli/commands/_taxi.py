"""``runway taxi`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any  # pylint: disable=W

import click

from .. import options
from ._plan import plan

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("taxi", short_help="alias of plan")
@options.ci
@options.debug
@options.deploy_environment
@options.no_color
@options.tags
@options.verbose
@click.pass_context
def taxi(ctx, **kwargs):
    # type: (click.Context, Any) -> None
    """Alias of "runway plan"."""
    LOGGER.verbose("forwarding to plan...")
    ctx.forward(plan, **kwargs)
