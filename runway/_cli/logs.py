"""Runway CLI logging setup."""
import logging
import sys
from typing import Any  # pylint: disable=W

from ..cfngin.logger import ColorFormatter

COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')


def setup_logging(*_, debug):
    # type: (Any, int) -> None
    """Configure log settings for Runway CLI.

    Args:
        debug: Debug level (0-2).

    """
    hdlr = logging.StreamHandler()
    hdlr.setFormatter(ColorFormatter(
        COLOR_FORMAT if sys.stdout.isatty() else logging.BASIC_FORMAT
    ))
    if debug >= 2:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO,
                            handlers=[hdlr])
        LOGGER.debug('setting botocore log level to ERROR')
        logging.getLogger('botocore').setLevel(logging.ERROR)

        if debug:
            LOGGER.setLevel(logging.DEBUG)
    LOGGER.debug('inatalized logging for Runway')
