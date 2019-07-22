"""The run-python command."""

import logging
import sys

from ..runway_command import RunwayCommand
from ...util import get_embedded_lib_path

LOGGER = logging.getLogger('runway')


class RunPython(RunwayCommand):
    """Extend RunwayCommand with execution of python files."""

    def execute(self):
        """Execute python script."""
        sys.path.insert(1, get_embedded_lib_path())
        with open(self._cli_arguments.get('<filename>'), 'r') as stream:
            exec(stream.read())  # pylint: disable=exec-used
