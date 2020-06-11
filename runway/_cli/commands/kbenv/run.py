"""Run a kubectl command."""
import logging
import subprocess
from typing import Tuple  # noqa pylint: disable=unused-import

import click

from ....env_mgr.kbenv import KBEnvManager

LOGGER = logging.getLogger(__name__)


@click.command('run', short_help='run kubectl',
               context_settings={'ignore_unknown_options': True})
@click.argument('args', metavar='<args>', nargs=-1)
@click.pass_context
def run(ctx, args):
    # type: (click.Context, Tuple[str, ...]) -> None
    """Run a kubectl command.

    Uses the version of kubectl specified in the ".kubectl-version" file
    in the current directory.

    IMPORTANT: When using options shared with Runway "--" must be placed
    before the kubectl command.

    """
    ctx.exit(subprocess.call([KBEnvManager().install()] + list(args)))
