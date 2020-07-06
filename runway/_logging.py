"""Runway logging."""
import logging
from enum import IntEnum


class LogLevels(IntEnum):
    """All available log levels."""

    NOTSET: int = 0
    DEBUG: int = 10
    VERBOSE: int = 15
    INFO: int = 20
    NOTICE: int = 25
    WARNING: int = 30
    SUCCESS: int = 35
    ERROR: int = 40
    CRITICAL: int = 50

    @classmethod
    def has_value(cls, value: int) -> bool:
        """Check if IntEnum has a value."""
        return value in cls._value2member_map_   # pylint: disable=no-member


class RunwayLogger(logging.Logger):
    """Extend built-in logger with additional levels."""

    def __init__(self, name, level=logging.NOTSET):
        """Instantiate the class.

        Args:
            name (str): Logger name.
            level (int): Log level.

        """
        super().__init__(name, level)
        logging.addLevelName(LogLevels.VERBOSE, LogLevels.VERBOSE.name)
        logging.addLevelName(LogLevels.NOTICE, LogLevels.NOTICE.name)
        logging.addLevelName(LogLevels.SUCCESS, LogLevels.SUCCESS.name)

    def verbose(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity `VERBOSE`.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        if self.isEnabledFor(LogLevels.VERBOSE):
            self._log(LogLevels.VERBOSE, msg, args, **kwargs)

    def notice(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity `NOTICE`.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        if self.isEnabledFor(LogLevels.NOTICE):
            self._log(LogLevels.NOTICE, msg, args, **kwargs)

    def success(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity `SUCCESS`.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        if self.isEnabledFor(LogLevels.SUCCESS):
            self._log(LogLevels.SUCCESS, msg, args, **kwargs)
