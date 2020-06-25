"""``runway whichenv`` command."""
import logging

import click

from ...util import SafeHaven


@click.command('whichenv', short_help='current deploy environment')
@click.pass_context
def whichenv(ctx):
    """Print the current deploy environment name to stdout."""
    logging.getLogger('runway').setLevel(logging.ERROR)  # suppress warnings
    with SafeHaven(environ={'CI': '1'}):  # prevent prompts
        click.echo(ctx.obj.env.name)
