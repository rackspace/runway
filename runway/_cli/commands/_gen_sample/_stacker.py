"""[DEPRECATED] Generate a sample CFNgin project using Blueprints."""
import logging

import click

from ._cfngin import cfngin

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('stacker', short_help='deprecated, use cfngin')
@click.pass_context
def stacker(ctx):
    # type: (click.Context) -> None
    """[DEPRECATED] Generate a sample CFNgin project using Blueprints."""
    LOGGER.warning('This command has been deprecated and will be removed in '
                   'the next major release.')
    LOGGER.debug('forwarding to cfngin...')
    ctx.forward(cfngin)
