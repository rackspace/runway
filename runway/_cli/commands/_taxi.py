"""``runway taxi`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from .. import options
from ._plan import plan

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('taxi', short_help='alias for plan')
@options.ci
@options.deploy_environment
@options.tags
@click.pass_context
def taxi(ctx, **kwargs):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Alias for "runway plan".

    Determine what infrastructure changes will occur during the next deploy.

    """
    LOGGER.debug('forwarding to plan...')
    ctx.forward(plan, **kwargs)
