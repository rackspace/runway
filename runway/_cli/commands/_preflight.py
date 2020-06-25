"""``runway preflight`` command."""
import logging

import click

from .. import options
from ._test import test

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('preflight', short_help='alias for test')
@options.deploy_environment
@click.pass_context
def preflight(ctx, **kwargs):
    """Alias for "runway test".

    Execute tests as defined in the Runway config.

    """
    LOGGER.debug('forwarding to test...')
    ctx.forward(test, **kwargs)
