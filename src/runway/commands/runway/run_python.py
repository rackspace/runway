"""Execute a python script using a bundled copy of python.

By using this command Runway can execute actions using a bundled copy of
python without requiring python to be installed on a system. This is only
applicable when installing the bundled version of Runway, not from
PyPI (``pip install runway``). When installed from PyPI, the system's
python is used.

Example:
  .. code-block:: shell

    $ runway run-python my-script.py

"""

import logging
import sys

from ..runway_command import RunwayCommand
from ...util import get_embedded_lib_path

LOGGER = logging.getLogger('runway')


class RunPython(RunwayCommand):
    """Extend RunwayCommand with execution of python files."""

    SKIP_FIND_CONFIG = True

    def execute(self):
        """Execute python script."""
        sys.path.insert(1, get_embedded_lib_path())
        with open(self._cli_arguments.get('<filename>'), 'r') as stream:
            exec(stream.read())  # pylint: disable=exec-used
