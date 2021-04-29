"""cfn-list test runner."""
from __future__ import annotations

import logging
import runpy
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Union

import yaml

from ..._logging import PrefixAdaptor
from ...utils import argv
from .base import TestHandler

if TYPE_CHECKING:
    from ...config.components.runway.base import ConfigProperty

TYPE_NAME = "cfn-lint"
LOGGER = logging.getLogger(__name__)


class CfnLintHandler(TestHandler):
    """Lints CFN."""

    @classmethod
    def handle(cls, name: str, args: Union[ConfigProperty, Dict[str, Any]]) -> None:
        """Perform the actual test.

        Relies on .cfnlintrc file to be located beside the Runway config file.

        """
        logger = PrefixAdaptor(name, LOGGER)
        cfnlintrc = Path("./.cfnlintrc")

        if not cfnlintrc.is_file():
            logger.error("file must exist to use this test: %s", cfnlintrc)
            sys.exit(1)

        # prevent duplicate log messages by not passing to the root logger
        logging.getLogger("cfnlint").propagate = False
        try:
            with argv(*["cfn-lint"] + args.get("cli_args", [])):
                runpy.run_module("cfnlint", run_name="__main__")
        except SystemExit as err:  # this call will always result in SystemExit
            if err.code != 0:  # ignore zero exit codes but re-raise for non-zero
                if not (yaml.safe_load(cfnlintrc.read_text()) or {}).get("templates"):
                    logger.warning(
                        'cfnlintrc is missing a "templates" '
                        "section which is required by cfn-lint"
                    )
                raise
