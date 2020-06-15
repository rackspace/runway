"""``runway preflight`` command."""
import logging

import click

from .test import test
from .. import options

LOGGER = logging.getLogger(__name__)


@click.command('preflight', short_help='alias from test')
@options.deploy_environment
@click.pass_context
def preflight(ctx, **kwargs):
    """Alias for "runway test".

    Execute tests as defined in the Runway config.

    """
    LOGGER.debug('forwarding to test...')
    ctx.forward(test, **kwargs)
