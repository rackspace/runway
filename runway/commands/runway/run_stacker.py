"""Execute the "shimmed" `Stacker`_ aka Runway CFNgin.

This command allows direct access to Runway's CloudFormation management
tool, Stacker.

Example:
  .. code-block:: shell

    $ runway run-stacker -- build example.env example.yaml

"""

import logging
import sys

from ..runway_command import RunwayCommand
from ...cfngin.logger import setup_logging
from ...cfngin.commands import Stacker
from ...util import get_embedded_lib_path, strip_leading_option_delim

LOGGER = logging.getLogger('runway')


class RunStacker(RunwayCommand):
    """Extend RunwayCommand with execution of Stacker."""

    SKIP_FIND_CONFIG = True

    def execute(self):
        """Execute stacker."""
        cmd_line_args = strip_leading_option_delim(
            self._cli_arguments.get('<stacker-args>', [])
        )
        # we don't have anything embedded anymore but probably worth keeping
        # the logic around.
        lib_path = get_embedded_lib_path()
        sys.argv = ['stacker'] + cmd_line_args
        sys.path.insert(1, lib_path)
        stacker = Stacker(setup_logging=setup_logging)
        args = stacker.parse_args(cmd_line_args)
        stacker.configure(args)
        args.run(args)
