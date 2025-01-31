"""Runway logging."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import MutableMapping


class LogLevels(IntEnum):
    """All available log levels."""

    NOTSET = 0
    DEBUG = 10
    VERBOSE = 15
    INFO = 20
    NOTICE = 25
    WARNING = 30
    SUCCESS = 35
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def has_value(cls, value: int) -> bool:
        """Check if IntEnum has a value."""
        return value in cls._value2member_map_


# Issue with this version of LoggerAdapter https://github.com/python/typeshed/issues/7855
class PrefixAdaptor(logging.LoggerAdapter):  # type: ignore
    """LoggerAdapter that adds prefixes to messages.

    Example:
        >>> logger = PrefixAdaptor("something", logging.getLogger("example"))
        ... logger.info("my message")

    """

    def __init__(
        self,
        prefix: str,
        logger: logging.Logger,
        prefix_template: str = "{prefix}:{msg}",
    ) -> None:
        """Instantiate class.

        Args:
            prefix: Message prefix.
            logger: Logger where the prefixed messages will be sent.
            prefix_template: String that can be used with
                ".format(prefix=<prefix>, msg=<msg>)" to produce a dynamic
                message prefix.

        """
        super().__init__(logger, {})
        self.prefix = prefix
        self.prefix_template = prefix_template

    def notice(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Delegate a notice call to the underlying logger.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.log(LogLevels.NOTICE, msg, *args, **kwargs)

    def process(
        self, msg: Exception | str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Process the message to append the prefix.

        Args:
            msg: Message to be prefixed.
            kwargs: Keyword args for the message.

        """
        return self.prefix_template.format(prefix=self.prefix, msg=msg), kwargs

    def setLevel(self, level: int | str) -> None:  # noqa: N802
        """Set the specified level on the underlying logger.

        Python 2 backport.

        """
        self.logger.setLevel(level)

    def success(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Delegate a success call to the underlying logger.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.log(LogLevels.SUCCESS, msg, *args, **kwargs)

    def verbose(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Delegate a verbose call to the underlying logger.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.log(LogLevels.VERBOSE, msg, *args, **kwargs)


class RunwayLogger(logging.Logger):
    """Extend built-in logger with additional levels."""

    def __init__(self, name: str, level: int | str = logging.NOTSET) -> None:
        """Instantiate the class.

        Args:
            name: Logger name.
            level: Log level.

        """
        super().__init__(name, level)
        logging.addLevelName(LogLevels.VERBOSE, LogLevels.VERBOSE.name)
        logging.addLevelName(LogLevels.NOTICE, LogLevels.NOTICE.name)
        logging.addLevelName(LogLevels.SUCCESS, LogLevels.SUCCESS.name)

    def notice(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Log 'msg % args' with severity `NOTICE`.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        if self.isEnabledFor(LogLevels.NOTICE):
            self._log(LogLevels.NOTICE, msg, args, **kwargs)

    def success(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Log 'msg % args' with severity `SUCCESS`.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        if self.isEnabledFor(LogLevels.SUCCESS):
            self._log(LogLevels.SUCCESS, msg, args, **kwargs)

    def verbose(self, msg: Exception | str, *args: Any, **kwargs: Any) -> None:
        """Log 'msg % args' with severity `VERBOSE`.

        Args:
            msg: String template or exception to use for the log record.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        if self.isEnabledFor(LogLevels.VERBOSE):
            self._log(LogLevels.VERBOSE, msg, args, **kwargs)
