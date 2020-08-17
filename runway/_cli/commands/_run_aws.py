"""``runway run-aws`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple  # noqa pylint: disable=unused-import

import click
from awscli.clidriver import create_clidriver

from ...util import SafeHaven
from .. import options


@click.command(
    "run-aws",
    short_help="bundled awscli",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("args", metavar="<args>", nargs=-1, required=True)
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def run_aws(ctx, args, **_):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Execute awscli commands using the version bundled with Runway.

    This command gives access to the awscli when it might not
    otherwise be installed (e.g. when using a binary release of Runway).

    IMPORTANT: When using options shared with Runway "--" must be placed
    before the awscli command.

    """
    if not ctx.obj.debug:
        # suppress awscli debug logs
        for name, logger in logging.getLogger("awscli").manager.loggerDict.items():
            if name.startswith("awscli.") and isinstance(logger, logging.Logger):
                logger.setLevel(logging.ERROR)
    with SafeHaven(environ={"LC_CTYPE": "en_US.UTF"}):
        ctx.exit(create_clidriver().main(list(args)))
