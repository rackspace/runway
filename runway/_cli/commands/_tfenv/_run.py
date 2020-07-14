"""Run a kubectl command."""
# docs: file://./../../../../docs/source/commands.rst
import logging
import subprocess
from typing import Any, Tuple  # noqa pylint: disable=W

import click

from ....env_mgr.tfenv import TFEnvManager
from ... import options

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('run', short_help='run terraform',
               context_settings={'ignore_unknown_options': True})
@click.argument('args', metavar='<args>', nargs=-1, required=True)
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def run(ctx, args, **_):
    # type: (click.Context, Tuple[str, ...], Any) -> None
    """Run a Terraform command.

    Uses the version of Terraform specified in the ".terraform-version" file
    in the current directory.

    IMPORTANT: When using options shared with Runway "--" must be placed
    before the Terraform command.

    """
    ctx.exit(subprocess.call([TFEnvManager().install()] + list(args)))
