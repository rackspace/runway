"""``runway dismantle`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from .. import options
from ._destroy import destroy

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('dismantle', short_help='alias for destroy')
@options.ci
@options.deploy_environment
@options.tags
@click.pass_context
def dismantle(ctx, **kwargs):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Alias for "runway destroy".

    Destroy infrastructure as code modules with Runway.

    """
    LOGGER.debug('forwarding to destroy...')
    ctx.forward(destroy, **kwargs)
