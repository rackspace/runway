"""Execute the "shimmed" `Stacker`_ aka Runway CFNgin.

This command allows direct access to Runway's CloudFormation management tool.

.. deprecated:: 1.5.0

Example:
  .. code-block:: shell

    $ runway run-stacker -- build example.env example.yaml

"""
import logging
import sys
import warnings

from ..runway_command import RunwayCommand
from ...cfngin.logger import setup_logging
from ...cfngin.commands import Stacker
from ...util import strip_leading_option_delim

LOGGER = logging.getLogger('runway')


class RunStacker(RunwayCommand):
    """Extend RunwayCommand with execution of Stacker."""

    SKIP_FIND_CONFIG = True

    def execute(self):
        """Execute stacker."""
        warnings.warn(self.DEPRECATION_MSG,
                      DeprecationWarning)
        LOGGER.warning(self.DEPRECATION_MSG)
        cmd_line_args = strip_leading_option_delim(
            self._cli_arguments.get('<stacker-args>', [])
        )
        sys.argv = ['stacker'] + cmd_line_args
        stacker = Stacker(setup_logging=setup_logging)
        args = stacker.parse_args(cmd_line_args)
        stacker.configure(args)
        args.run(args)
