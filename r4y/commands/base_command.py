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
                 r4y_config_dir=None  # type: Optional[str]
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
            self.r4y_config_path = None
            self._r4y_config = None
            return

        # This may be invoked from a module directory in an environment;
        # account for that here if necessary
        try:
            # Disable other r4y logging so the only response is the env name
            logging.getLogger('r4y').setLevel(logging.CRITICAL)
            self.r4y_config_path = Config.find_config_file(r4y_config_dir or
                                                              self.env_root)
        except SystemExit:
            logging.getLogger('r4y').setLevel(logging.WARN)
            self.env_root = os.path.dirname(os.getcwd())
            self.r4y_config_path = Config.find_config_file(self.env_root)
        logging.getLogger('r4y').setLevel(logging.INFO)
        self._r4y_config = None

    @property
    def r4y_config(self):
        # type: () -> Config
        """Return parsed r4y.yml."""
        if not self._r4y_config:
            self._r4y_config = Config.load_from_file(
                self.r4y_config_path
            )
        return self._r4y_config

    @property
    def r4y_vars(self):
        # type: () -> VariablesDefinition
        """Return parsed Runway variables."""
        return self.r4y_config.variables

    def execute(self):
        # type: () -> None
        """Execute the command."""
        raise NotImplementedError('execute must be implimented for '
                                  'subclasses of BaseCommand.')
