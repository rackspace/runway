"""Runway CLI entrypoint."""
import argparse
import logging
import os
from typing import Any, Dict  # pylint: disable=W

import click

from runway import __version__

from . import commands, options
from .logs import setup_logging
from .utils import CliContext

LOGGER = logging.getLogger("runway.cli")

CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=999)


class _CliGroup(click.Group):  # pylint: disable=too-few-public-methods
    """Extends the use of click.Group.

    This should only be used for the main application group.

    """

    def invoke(self, ctx):
        # type: (click.Context) -> Any
        """Replace invoke command to pass along args."""
        ctx.meta["global.options"] = self.__parse_global_options(ctx)
        return super(_CliGroup, self).invoke(ctx)

    @staticmethod
    def __parse_global_options(ctx):
        # type: (click.Context) -> Dict[str, Any]
        """Parse global options.

        These options are passed to subcommands but, should be parsed by the
        main application group. The value of these options are used for global
        configuration such as logging or context object setup.

        """
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--ci", action="store_true", default=bool(os.getenv("CI")))
        parser.add_argument(
            "--debug", default=int(os.getenv("DEBUG", "0")), action="count"
        )
        parser.add_argument(
            "-e", "--deploy-environment", default=os.getenv("DEPLOY_ENVIRONMENT")
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            default=bool(os.getenv("RUNWAY_NO_COLOR")),
        )
        parser.add_argument(
            "--verbose", action="store_true", default=bool(os.getenv("VERBOSE"))
        )
        args, _ = parser.parse_known_args(list(ctx.args))
        return vars(args)


@click.group(context_settings=CLICK_CONTEXT_SETTINGS, cls=_CliGroup)
@click.version_option(__version__, message="%(version)s")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def cli(ctx, **_):
    # type: (click.Context, Any) -> None
    """Runway CLI.

    Full documentation available at https://docs.onica.com/projects/runway/.

    """
    opts = ctx.meta["global.options"]
    setup_logging(
        debug=opts["debug"], no_color=opts["no_color"], verbose=opts["verbose"]
    )
    ctx.obj = CliContext(**opts)


# register all the other commands from the importable modules defined
# in commands.
for cmd in commands.__all__:
    cli.add_command(getattr(commands, cmd))
