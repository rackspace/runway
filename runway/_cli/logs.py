"""Runway CLI logging setup."""
import logging
import os
from typing import Any, Dict

import coloredlogs

from runway import LogLevels

from ..compat import cached_property

# COLOR_FORMAT = "%(levelname)s:%(name)s:\033[%(color)sm%(message)s\033[39m"
LOGGER = logging.getLogger("runway")

LOG_FORMAT = "[runway] %(message)s"
LOG_FORMAT_VERBOSE = logging.BASIC_FORMAT
LOG_FIELD_STYLES: Dict[str, Dict[str, Any]] = {
    "asctime": {},
    "hostname": {},
    "levelname": {},
    "message": {},
    "name": {},
    "prefix": {},
    "programname": {},
}
LOG_LEVEL_STYLES: Dict[str, Dict[str, Any]] = {
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


class LogSettings:
    """CLI log settings."""

    ENV = {
        "field_styles": os.getenv("RUNWAY_LOG_FIELD_STYLES"),
        "fmt": os.getenv("RUNWAY_LOG_FORMAT"),
        "level_styles": os.getenv("RUNWAY_LOG_LEVEL_STYLES"),
    }

    def __init__(
        self, *, debug: int = 0, no_color: bool = False, verbose: bool = False
    ):
        """Instantiate class.

        Args:
            debug: Debug level.
            no_color: Disable color in Runway's logs.
            verbose: Whether to display verbose logs.

        """
        self.debug = debug
        self.no_color = no_color
        self.verbose = verbose

    @property
    def coloredlogs(self) -> Dict[str, Any]:
        """Return settings for coloredlogs."""
        return {
            "fmt": self.fmt,
            "field_styles": self.field_styles,
            "level_styles": self.level_styles,
        }

    @cached_property
    def fmt(self) -> str:
        """Return log record format.

        If "RUNWAY_LOG_FORMAT" exists in the environment, it will be used.

        """
        fmt = self.ENV["fmt"]
        if isinstance(fmt, str):
            return fmt
        if self.debug or self.no_color or self.verbose:
            return LOG_FORMAT_VERBOSE
        return LOG_FORMAT

    @cached_property
    def field_styles(self) -> Dict[str, Any]:
        """Return log field styles.

        If "RUNWAY_LOG_FIELD_STYLES" exists in the environment, it will be
        used to update the Runway LOG_FIELD_STYLES.

        """
        if self.no_color:
            return {}

        result = LOG_FIELD_STYLES.copy()
        if self.ENV["field_styles"]:
            result.update(
                coloredlogs.parse_encoded_styles(  # type: ignore
                    self.ENV["field_styles"]
                )
            )
        return result

    @cached_property
    def level_styles(self) -> Dict[str, Any]:
        """Return log level styles.

        If "RUNWAY_LOG_LEVEL_STYLES" exists in the environment, it will be
        used to update the Runway LOG_LEVEL_STYLES.

        """
        if self.no_color:
            return {}

        result = LOG_LEVEL_STYLES.copy()
        if self.ENV["level_styles"]:
            result.update(
                coloredlogs.parse_encoded_styles(  # type: ignore
                    self.ENV["level_styles"]
                )
            )
        return result

    @cached_property
    def log_level(self) -> LogLevels:
        """Return log level to use."""
        if self.debug:
            return LogLevels.DEBUG
        if self.verbose:
            return LogLevels.VERBOSE
        return LogLevels.INFO


def setup_logging(
    *, debug: int = 0, no_color: bool = False, verbose: bool = False
) -> None:
    """Configure log settings for Runway CLI.

    Keyword Args:
        debug: Debug level (0-2).
        no_color: Whether to use colorized logs.
        verbose: Use verbose logging.

    """
    settings = LogSettings(debug=debug, no_color=no_color, verbose=verbose)

    coloredlogs.install(settings.log_level, logger=LOGGER, **settings.coloredlogs)
    LOGGER.debug("runway log level: %s", LOGGER.getEffectiveLevel())

    if settings.debug == 2:
        coloredlogs.install(
            settings.log_level,
            logger=logging.getLogger("botocore"),
            **settings.coloredlogs,
        )
        LOGGER.debug("set dependency log level to debug")
    LOGGER.debug("initalized logging for Runway")
