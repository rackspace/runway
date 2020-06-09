"""Runway CLI entrypoint."""
import logging
import sys

import click

from runway import __version__

from ..cfngin.logger import ColorFormatter
from . import commands

COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')
HDLR = logging.StreamHandler()
HDLR.setFormatter(ColorFormatter(
    COLOR_FORMAT if sys.stdout.isatty() else logging.BASIC_FORMAT
))
logging.basicConfig(level=logging.INFO,
                    handlers=[HDLR])
# botocore info is spammy
logging.getLogger('botocore').setLevel(logging.ERROR)

CLICK_CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    max_content_width=999
)


@click.group(context_settings=CLICK_CONTEXT_SETTINGS)
@click.version_option(__version__, message='%(version)s')
def cli():
    # type: () -> None
    """Runway CLI."""


# register all the other commands from the importable modules defined
# in commands.
for cmd in commands.__all__:
    cli.add_command(getattr(commands, cmd))


def main():
    # type: () -> None
    """Runway CLI entrypoint."""
    cli.main()
