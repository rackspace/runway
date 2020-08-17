"""``runway gen-sample stacker`` command."""
import logging
from typing import Any  # pylint: disable=W

import click

from ... import options
from ._cfngin import cfngin

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("stacker", short_help="deprecated, use cfngin")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def stacker(ctx, **kwargs):
    # type: (click.Context, Any) -> None
    """[DEPRECATED] Generate a sample CFNgin project using Blueprints."""  # noqa
    LOGGER.warning(
        "This command has been deprecated and will be removed in "
        "the next major release."
    )
    LOGGER.verbose("forwarding to cfngin...")
    ctx.forward(cfngin, **kwargs)
