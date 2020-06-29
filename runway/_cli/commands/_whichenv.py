"""``runway whichenv`` command."""
import logging

import click

from ...util import SafeHaven
from .. import options


@click.command('whichenv', short_help='current deploy environment')
@options.debug
@click.pass_context
def whichenv(ctx, **_):
    """Print the current deploy environment name to stdout."""
    if not ctx.obj.debug:
        logging.getLogger('runway').setLevel(logging.ERROR)  # suppress warnings
    with SafeHaven(environ={'CI': '1'}):  # prevent prompts
        click.echo(ctx.obj.env.name)
