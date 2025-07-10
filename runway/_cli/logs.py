"""Runway CLI logging setup."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, TextIO

import coloredlogs
from humanfriendly.terminal import terminal_supports_colors  # type: ignore
from typing_extensions import TypedDict

from .. import LogLevels
from ..compat import cached_property
from ..utils import str_to_bool

LOGGER = logging.getLogger("runway")

LOG_FORMAT = "[runway] %(message)s"
LOG_FORMAT_VERBOSE = logging.BASIC_FORMAT
LOG_FIELD_STYLES: dict[str, dict[str, Any]] = {
    "asctime": {},
    "hostname": {},
    "levelname": {},
    "message": {},
    "name": {},
    "prefix": {},
    "programname": {},
}
LOG_LEVEL_STYLES: dict[str, dict[str, Any]] = {
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


class LogSettingsEnvTypeDef(TypedDict):
    """Type definition for :attr:`runway._cli.logs.LogSettings._env` attribute."""

    field_styles: str | None
    fmt: str | None
    level_styles: str | None


class LogSettings:
    """CLI log settings."""

    _env: LogSettingsEnvTypeDef

    def __init__(self, *, debug: int = 0, no_color: bool = False, verbose: bool = False) -> None:
        """Instantiate class.

        Args:
            debug: Debug level.
            no_color: Disable color in Runway's logs.
            verbose: Whether to display verbose logs.

        """
        self._env = {
            "field_styles": os.getenv("RUNWAY_LOG_FIELD_STYLES"),
            "fmt": os.getenv("RUNWAY_LOG_FORMAT"),
            "level_styles": os.getenv("RUNWAY_LOG_LEVEL_STYLES"),
        }
        self.debug = debug
        self.no_color = no_color
        self.verbose = verbose

    @property
    def coloredlogs(self) -> dict[str, Any]:
        """Return settings for coloredlogs."""
        return {
            "field_styles": self.field_styles,
            "fmt": self.fmt,
            "isatty": None if self.no_color else self.supports_colors,
            "level_styles": self.level_styles,
            "stream": self.stream,
        }

    @cached_property
    def fmt(self) -> str:
        """Return log record format.

        If "RUNWAY_LOG_FORMAT" exists in the environment, it will be used.

        """
        fmt = self._env["fmt"]
        if isinstance(fmt, str) and fmt:
            return fmt
        if self.debug or self.no_color or self.verbose:
            return LOG_FORMAT_VERBOSE
        return LOG_FORMAT

    @cached_property
    def field_styles(self) -> dict[str, Any]:
        """Return log field styles.

        If "RUNWAY_LOG_FIELD_STYLES" exists in the environment, it will be
        used to update the Runway LOG_FIELD_STYLES.

        """
        if self.no_color:
            return {}

        result = LOG_FIELD_STYLES.copy()
        if self._env["field_styles"]:
            result.update(
                coloredlogs.parse_encoded_styles(self._env["field_styles"])  # type: ignore
            )
        return result

    @cached_property
    def level_styles(self) -> dict[str, Any]:
        """Return log level styles.

        If "RUNWAY_LOG_LEVEL_STYLES" exists in the environment, it will be
        used to update the Runway LOG_LEVEL_STYLES.

        """
        if self.no_color:
            return {}

        result = LOG_LEVEL_STYLES.copy()
        if self._env["level_styles"]:
            result.update(
                coloredlogs.parse_encoded_styles(self._env["level_styles"])  # type: ignore
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

    @property
    def stream(self) -> TextIO:
        """Stream that will be logged to."""
        return sys.stdout

    @cached_property
    def supports_colors(self) -> bool:
        """Return if ``stream`` is connected to a terminal that supports ANSI escape sequences."""
        if str_to_bool(os.getenv("GITLAB_CI")):
            # GitLab does not use a TTY which is necessary for `terminal_supports_colors`/
            #   `coloredlogs.install()` to autodetect color support.
            return True
        return terminal_supports_colors(self.stream)  # type: ignore


def setup_logging(*, debug: int = 0, no_color: bool = False, verbose: bool = False) -> None:
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
    LOGGER.debug("initialized logging for Runway")
