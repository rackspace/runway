"""``runway run-aws`` command."""
import logging
import os
from typing import Tuple  # noqa pylint: disable=unused-import

import click
from awscli.clidriver import create_clidriver

from ...util import SafeHaven


@click.command('run-aws', short_help='bundled awscli',
               context_settings={'ignore_unknown_options': True})
@click.argument('args', metavar='<args>', nargs=-1, required=True)
@click.pass_context
def run_aws(ctx, args):
    # type: (click.Context, Tuple[str, ...]) -> None
    """Execute awscli commands using the version bundled with Runway.

    This command gives access to the awscli when it might not
    otherwise be installed (e.g. when using a binary release of Runway).

    IMPORTANT: When using options shared with Runway "--" must be placed
    before the awscli command.

    """
    if not os.environ.get('DEBUG') and '--debug' not in args:
        # suppress awscli debug logs
        for name, logger in logging.getLogger('awscli').manager.loggerDict.items():
            if name.startswith('awscli.') and isinstance(logger, logging.Logger):
                logger.setLevel(logging.ERROR)
    with SafeHaven(environ={'LC_CTYPE': 'en_US.UTF'}):
        ctx.exit(create_clidriver().main(list(args)))
