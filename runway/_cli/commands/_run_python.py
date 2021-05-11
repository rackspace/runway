"""``runway run-python`` command."""
# docs: file://./../../../docs/source/commands.rst
from pathlib import Path
from typing import Any

import click

from .. import options


@click.command("run-python", short_help="bundled python")
@click.argument(
    "filename",
    metavar="<filename>",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@options.debug
@options.no_color
@options.verbose
def run_python(filename: str, **_: Any) -> None:
    """Execute a python script using a bundled copy of python.

    This command can execute actions using python without requiring python to
    be installed on a system.
    This is only applicable when installing a binary release of Runway
    (not installed from PyPi).
    When installed from PyPI, the current interpreter is used.

    """
    execglobals = globals().copy()
    # override name & file so script operates as if it were invoked directly
    execglobals.update({"__name__": "__main__", "__file__": filename})
    exec(  # pylint: disable=exec-used
        Path(filename).read_text(), execglobals, execglobals
    )
