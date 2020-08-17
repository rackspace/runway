"""Runway CLI logging setup."""
import logging
import os

import coloredlogs

from runway import LogLevels

from ..util import cached_property

# COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger("runway")

LOG_FORMAT = "[%(programname)s] %(message)s"
LOG_FORMAT_VERBOSE = logging.BASIC_FORMAT
LOG_FIELD_STYLES = {
    "asctime": {},
    "hostname": {},
    "levelname": {},
    "message": {},
    "name": {},
    "prefix": {},
    "programname": {},
}
LOG_LEVEL_STYLES = {
    "critical": {"color": "red", "bold": True},
    "debug": {"color": "green"},
    "error": {"color": "red"},
    "info": {},
    "notice": {"color": "yellow"},
    "spam": {"color": "green", "faint": True},
    "success": {"color": "green", "bold": True},
    "verbose": {"color": "cyan"},
    "warning": {"color": 214},
}


class LogSettings(object):
    """CLI log settings."""

    ENV = {
        "field_styles": os.getenv("RUNWAY_LOG_FIELD_STYLES"),
        "fmt": os.getenv("RUNWAY_LOG_FORMAT"),
        "level_styles": os.getenv("RUNWAY_LOG_LEVEL_STYLES"),
    }

    def __init__(self, debug=0, no_color=False, verbose=False):
        """Instantiate class.

        Args:
            debug (int): Debug level.
            no_color (bool): Disable color in Runway's logs.
            verbose (bool): Whether to display verbose logs.

        """
        self.debug = debug
        self.no_color = no_color
        self.verbose = verbose

    @property
    def coloredlogs(self):
        """Return settings for coloredlogs.

        Returns:
            Dict[str, Any]

        """
        return {
            "fmt": self.fmt,
            "field_styles": self.field_styles,
            "level_styles": self.level_styles,
        }

    @cached_property
    def fmt(self):
        """Return log record format.

        If "RUNWAY_LOG_FORMAT" exists in the environment, it will be used.

        Returns:
            str

        """
        if self.ENV["fmt"]:
            return self.ENV["fmt"]
        if self.debug or self.no_color or self.verbose:
            return LOG_FORMAT_VERBOSE
        return LOG_FORMAT

    @cached_property
    def field_styles(self):
        """Return log field styles.

        If "RUNWAY_LOG_FIELD_STYLES" exists in the environment, it will be
        used to update the Runway LOG_FIELD_STYLES.

        Returns:
            Dict[str, Any]

        """
        if self.no_color:
            return {}

        result = LOG_FIELD_STYLES.copy()
        if self.ENV["field_styles"]:
            result.update(coloredlogs.parse_encoded_styles(self.ENV["field_styles"]))
        return result

    @cached_property
    def level_styles(self):
        """Return log level styles.

        If "RUNWAY_LOG_LEVEL_STYLES" exists in the environment, it will be
        used to update the Runway LOG_LEVEL_STYLES.

        Returns:
            Dict[str, Any]

        """
        if self.no_color:
            return {}

        result = LOG_LEVEL_STYLES.copy()
        if self.ENV["level_styles"]:
            result.update(coloredlogs.parse_encoded_styles(self.ENV["level_styles"]))
        return result

    @cached_property
    def log_level(self):
        """Return log level to use.

        Returns:
            LogLevel

        """
        if self.debug:
            return LogLevels.DEBUG
        if self.verbose:
            return LogLevels.VERBOSE
        return LogLevels.INFO


# TODO implement propper keyword-only args when dropping python 2
def setup_logging(*_, **kwargs):
    """Configure log settings for Runway CLI.

    Keyword Args:
        debug (int): Debug level (0-2).

    """
    settings = LogSettings(
        debug=kwargs.pop("debug", 0),
        no_color=kwargs.pop("no_color", False),
        verbose=kwargs.pop("verbose", False),
    )

    coloredlogs.install(settings.log_level, logger=LOGGER, **settings.coloredlogs)
    LOGGER.debug("runway log level: %s", LOGGER.getEffectiveLevel())

    if settings.debug == 2:
        coloredlogs.install(
            settings.log_level,
            logger=logging.getLogger("botocore"),
            **settings.coloredlogs
        )
        LOGGER.debug("set dependency log level to debug")
    LOGGER.debug("initalized logging for Runway")
