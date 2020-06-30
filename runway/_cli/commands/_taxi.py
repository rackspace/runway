"""``runway taxi`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from .. import options
from ._plan import plan

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('taxi', short_help='alias of plan')
@options.ci
@options.debug
@options.deploy_environment
@options.tags
@click.pass_context
def taxi(ctx, **kwargs):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Alias of "runway plan"."""
    LOGGER.debug('forwarding to plan...')
    ctx.forward(plan, **kwargs)
