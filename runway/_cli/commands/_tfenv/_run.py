"""Run a kubectl command."""
import logging
import subprocess
from typing import Tuple  # noqa pylint: disable=unused-import

import click

from ....env_mgr.tfenv import TFEnvManager

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('run', short_help='run terraform',
               context_settings={'ignore_unknown_options': True})
@click.argument('args', metavar='<args>', nargs=-1, required=True)
@click.pass_context
def run(ctx, args):
    # type: (click.Context, Tuple[str, ...]) -> None
    """Run a Terraform command.

    Uses the version of Terraform specified in the ".terraform-version" file
    in the current directory.

    IMPORTANT: When using options shared with Runway "--" must be placed
    before the Terraform command.

    """
    ctx.exit(subprocess.call([TFEnvManager().install()] + list(args)))
