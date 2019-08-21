"""Base class for commands that need to parse the runway config."""
from typing import List, Union  # pylint: disable=unused-import
import os
import logging

from ..config import Config


class BaseCommand(object):
    """Base class for commands."""

    def __init__(self,
                 cli_arguments,  # type: List[Union[str, list, bool]]
                 env_root=None,  # type: str
                 runway_config_dir=None  # type: str
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """Initialize base class."""
        self._cli_arguments = cli_arguments

        if env_root is None:
            self.env_root = os.getcwd()
        else:
            self.env_root = env_root

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

    def execute(self):
        # type: () -> None
        """Execute the command."""
        raise NotImplementedError('execute must be implimented for '
                                  'subclasses of BaseCommand.')
