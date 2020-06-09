"""Runway CLI entrypoint."""
import sys

import click

from . import commands
from runway import __version__


CLICK_CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    max_content_width=999
)


@click.group(context_settings=CLICK_CONTEXT_SETTINGS)
@click.version_option(__version__, message='%(version)s')
@click.pass_context
def cli(ctx):
    # type: (click.Context) -> None
    """Runway CLI."""


# register all the other commands from the importable modules defined
# in commands.
for cmd in commands.__all__:
    cli.add_command(getattr(commands, cmd))


def main():
    # type: () -> None
    """Runway CLI entrypoint."""
    cli.main()
