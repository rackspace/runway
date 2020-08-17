"""``runway run-stacker`` command."""
# docs: file://./../../../docs/source/commands.rst
import logging
from typing import Any, Tuple  # noqa pylint: disable=unused-import

import click

from ...cfngin.commands import Stacker
from ...cfngin.logger import setup_logging
from ...util import SafeHaven
from .. import options

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command(
    "run-stacker",
    short_help="deprecated, bundled stacker",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("args", metavar="<args>", nargs=-1, required=True)
@options.debug
@options.no_color
@options.verbose
def run_stacker(args, **_):
    # type: (Tuple[str, ...], Any) -> None
    """Execute a command using the "shimmed" Stacker (aka CFNgin).

    Depreacted since version 1.5.0.

    """
    LOGGER.warning(
        "This command as been deprecated and will be removed in "
        "the next major release."
    )
    arg_list = list(args)
    with SafeHaven(argv=["stacker"] + arg_list):
        stacker = Stacker(setup_logging=setup_logging)
        cmd = stacker.parse_args(arg_list)
        stacker.configure(cmd)
        cmd.run(cmd)
