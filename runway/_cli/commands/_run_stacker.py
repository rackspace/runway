"""``runway run-stacker`` command."""
import logging
from typing import Tuple  # noqa pylint: disable=unused-import

import click

from ...cfngin.logger import setup_logging
from ...cfngin.commands import Stacker
from ...util import SafeHaven

LOGGER = logging.getLogger(__name__.replace('._', '.'))


@click.command('run-stacker', short_help='deprecated, bundled stacker',
               context_settings={'ignore_unknown_options': True})
@click.argument('args', metavar='<args>', nargs=-1, required=True)
def run_stacker(args):
    # type: (Tuple[str, ...]) -> None
    """Execute a command using the "shimmed" Stacker (aka CFNgin).

    Depreacted since version 1.5.0.

    """
    LOGGER.warning('This command as been deprecated and will be removed in '
                   'the next major release.')
    arg_list = list(args)
    with SafeHaven(argv=['stacker'] + arg_list):
        stacker = Stacker(setup_logging=setup_logging)
        cmd = stacker.parse_args(arg_list)
        stacker.configure(cmd)
        cmd.run(cmd)
