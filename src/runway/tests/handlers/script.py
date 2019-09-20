"""Script test runner."""
import logging
import sys
import subprocess
from subprocess import CalledProcessError
from typing import Dict, Any  # pylint: disable=unused-import

from runway.tests.handlers.base import TestHandler

TYPE_NAME = 'script'
LOGGER = logging.getLogger('runway')


class ScriptHandler(TestHandler):
    """Handle script tests.

    Args:
        commands (List[str]): A list of commands to be executed in order.
            Each command is run in its own subprocess. The working directory
            will be the same as where the 'runway test' command was executed.

    Example:
        tests:
          - name: example-test
            type: script
            args:
              commands:
                - echo "this is an example"
                - pwd

    """

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Perform the actual test."""
        for cmd in args['commands']:
            try:
                exit_code = subprocess.call(cmd, shell=True)
                if exit_code != 0:
                    raise ValueError(exit_code)
            except CalledProcessError as err:
                LOGGER.error('%s: failed to execute command: %s',
                             name, cmd)
                raise err
            except ValueError:
                LOGGER.error('%s: failed command: %s', name, cmd)
                sys.exit(1)
