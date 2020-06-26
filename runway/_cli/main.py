"""Runway CLI entrypoint."""
import argparse
import logging
import os
import sys
from typing import Any, Dict  # pylint: disable=W

import click

from runway import __version__

from ..cfngin.logger import ColorFormatter
from . import commands
from .utils import CliContext

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


class _CliGroup(click.Group):  # pylint: disable=too-few-public-methods
    """Extends the use of click.Group.

    This should only be used for the main application group.

    """

    def invoke(self, ctx):
        # type: (click.Context) -> Any
        """Replace invoke command to pass along args."""
        ctx.meta['global.options'] = self.__parse_global_options(ctx)
        return super(_CliGroup, self).invoke(ctx)

    @staticmethod
    def __parse_global_options(ctx):
        # type: (click.Context) -> Dict[str, Any]
        """Parse global options.

        These options are passed to subcommands but, should be parsed by the
        main application group. The value of these options are used for global
        configuration such as logging or context object setup.

        """
        if isinstance(ctx.args, (list, tuple)):
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('--ci', action='store_true',
                                default=bool(os.getenv('CI')))
            parser.add_argument('-e', '--deploy-environment',
                                default=os.getenv('DEPLOY_ENVIRONMENT'))
            args, _ = parser.parse_known_args(list(ctx.args))
            return vars(args)
        return {}


@click.group(context_settings=CLICK_CONTEXT_SETTINGS, cls=_CliGroup)
@click.version_option(__version__, message='%(version)s')
@click.pass_context
def cli(ctx):
    # type: (click.Context) -> None
    """Runway CLI.

    Full documentation available at https://docs.onica.com/projects/runway/.

    """
    ctx.obj = CliContext(**ctx.meta['global.options'])


# register all the other commands from the importable modules defined
# in commands.
for cmd in commands.__all__:
    cli.add_command(getattr(commands, cmd))


def main():
    # type: () -> None
    """Runway CLI entrypoint."""
    cli.main()
