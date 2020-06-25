"""``runway run-aws`` command."""
import sys

import click

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E


@click.command('run-python', short_help='bundled python')
@click.argument('filename', metavar='<filename>', required=True,
                type=click.Path(exists=True, dir_okay=False))
def run_python(filename):
    # type: (str) -> None
    """Execute a python script using a bundled copy of python.

    This command can execute actions using python without requiring python to
    be installed on a system. This is only applicable when installing a binary
    release of Runway (not installed from PyPi). When installed from PyPI,
    the current interpreter is used.

    """
    execglobals = globals().copy()
    # override name & file so script operates as if it were invoked directly
    execglobals.update({'__name__': '__main__',
                        '__file__': filename})
    exec(Path(filename).read_text(),  # pylint: disable=exec-used
         execglobals, execglobals)
