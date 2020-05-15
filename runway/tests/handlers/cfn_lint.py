"""cfn-list test runner."""
import logging
import runpy
import sys
from typing import Any, Dict  # pylint: disable=unused-import

import yaml

from ...util import argv
from .base import TestHandler

if sys.version_info.major < 3:
    from pathlib2 import Path  # pylint: disable=E
else:
    from pathlib import Path  # pylint: disable=E

TYPE_NAME = 'cfn-lint'
LOGGER = logging.getLogger('runway')


class CfnLintHandler(TestHandler):
    """Lints CFN."""

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Perform the actual test.

        Relies on .cfnlintrc file to be located beside the Runway config file.

        """
        cfnlintrc = Path('./.cfnlintrc')

        if not cfnlintrc.is_file():
            LOGGER.error('File must exist to use this test: %s', cfnlintrc)
            sys.exit(1)

        # prevent duplicate log messages by not passing to the root logger
        logging.getLogger('cfnlint').propagate = False
        try:
            with argv(*['cfn-lint'] + args.get('cli_args', [])):
                runpy.run_module('cfnlint', run_name='__main__')
        except SystemExit as err:  # this call will always result in SystemExit
            if err.code != 0:  # ignore zero exit codes but re-raise for non-zero
                if not (yaml.safe_load(cfnlintrc.read_text()) or
                        {}).get('templates'):
                    LOGGER.warning('cfnlintrc is missing a "templates" '
                                   'section which is required by cfn-lint')
                raise
