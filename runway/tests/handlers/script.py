"""Script test runner."""
from __future__ import annotations

import logging
import subprocess
import sys
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, Dict, Union

from ..._logging import PrefixAdaptor
from ...tests.handlers.base import TestHandler

if TYPE_CHECKING:
    from ...config.components.runway.base import ConfigProperty

TYPE_NAME = "script"
LOGGER = logging.getLogger(__name__)


class ScriptHandler(TestHandler):
    """Handle script tests.

    Args:
        commands (List[str]): A list of commands to be executed in order.
            Each command is run in its own subprocess. The working directory
            will be the same as where the 'runway test' command was executed.

    .. rubric:: Example
    .. code-block: yaml

        tests:
          - name: example-test
            type: script
            args:
              commands:
                - echo "this is an example"
                - pwd

    """

    @classmethod
    def handle(cls, name: str, args: Union[ConfigProperty, Dict[str, Any]]) -> None:
        """Perform the actual test."""
        logger = PrefixAdaptor(name, LOGGER)
        for cmd in args["commands"]:
            try:
                exit_code = subprocess.call(cmd, shell=True)
                if exit_code != 0:
                    raise ValueError(exit_code)
            except CalledProcessError as err:
                logger.error("failed to execute command: %s", cmd)
                raise err
            except ValueError:
                logger.error("failed command: %s", cmd)
                sys.exit(1)
