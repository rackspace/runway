"""Runway CLI logging setup."""
import logging
import sys

from ..cfngin.logger import ColorFormatter

COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger('runway')


# TODO implement propper keyword-only args when dropping python 2
# def setup_logging(*: Any, debug: int) -> None:
def setup_logging(_=None, **kwargs):
    """Configure log settings for Runway CLI.

    Args:
        debug (int): Debug level (0-2).

    """
    debug = kwargs.pop('debug', 0)
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
