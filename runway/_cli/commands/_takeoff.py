"""``runway takeoff`` command."""
import logging
from typing import Any, Tuple  # pylint: disable=W

import click

from .. import options
from ._deploy import deploy

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('takeoff', short_help='alias for deploy')
@options.ci
@options.debug
@options.deploy_environment
@options.tags
@click.pass_context
def takeoff(ctx, **kwargs):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Alias for "runway deploy".

    Deploy infrastructure as code modules with Runway.

    """
    LOGGER.debug('forwarding to deploy...')
    ctx.forward(deploy, **kwargs)
