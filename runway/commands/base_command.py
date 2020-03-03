"""Base class for commands that need to parse the Runway config."""
from typing import List, Optional, Union  # pylint: disable=unused-import
import os
import logging

from ..config import Config, VariablesDefinition  # noqa: F401 pylint: disable=unused-import


class BaseCommand(object):
    """Base class for commands."""

    DEPRECATION_MSG = ('This command as been deprecated and will be removed '
                       'in the next major release.')
    SKIP_FIND_CONFIG = False  # set to true for commands that don't need config

    def __init__(self,
                 cli_arguments,  # type: List[Union[str, list, bool]]
                 env_root=None,  # type: Optional[str]
                 runway_config_dir=None  # type: Optional[str]
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """Initialize base class."""
        self._cli_arguments = cli_arguments

        if env_root is None:
            self.env_root = os.getcwd()
        else:
            self.env_root = env_root

        if self.SKIP_FIND_CONFIG:
            self.runway_config_path = None
            self._runway_config = None
            return

        # This may be invoked from a module directory in an environment;
        # account for that here if necessary
        try:
            # Disable other runway logging so the only response is the env name
            logging.getLogger('runway').setLevel(logging.CRITICAL)
            self.runway_config_path = Config.find_config_file(runway_config_dir or
                                                              self.env_root)
        except SystemExit:
            logging.getLogger('runway').setLevel(logging.WARN)
            self.env_root = os.path.dirname(os.getcwd())
            self.runway_config_path = Config.find_config_file(self.env_root)
        logging.getLogger('runway').setLevel(logging.INFO)
        self._runway_config = None

    @property
    def runway_config(self):
        # type: () -> Config
        """Return parsed runway.yml."""
        if not self._runway_config:
            self._runway_config = Config.load_from_file(
                self.runway_config_path
            )
        return self._runway_config

    @property
    def runway_vars(self):
        # type: () -> VariablesDefinition
        """Return parsed Runway variables."""
        return self.runway_config.variables

    def execute(self):
        # type: () -> None
        """Execute the command."""
        raise NotImplementedError('execute must be implimented for '
                                  'subclasses of BaseCommand.')
