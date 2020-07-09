"""Runway logging."""
import logging
from enum import IntEnum


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
    def has_value(cls, value):
        """Check if IntEnum has a value."""
        return value in cls._value2member_map_   # pylint: disable=no-member


class PrefixAdaptor(logging.LoggerAdapter):
    """LoggerAdapter that adds prefixes to messages.

    Example:
        >>> logger = PrefixAdaptor('something', logging.getLogger('example'))
        ... logger.info('my message')

    """

    def __init__(self, prefix, logger, prefix_template='{prefix}:{msg}'):
        """Instantiate class.

        Args:
            prefix (str): Message prefix.
            logger (logging.Logger): Logger where the prefixed messages will
                be sent.
            prefix_template (str): String that can be used with
                ".format(prefix=<prefix>, msg=<msg>)" to produce a dynamic
                message prefix.

        """
        super(PrefixAdaptor, self).__init__(logger, {})
        self.prefix = prefix
        self.prefix_template = prefix_template

    def notice(self, msg, *args, **kwargs):
        """Delegate a notice call to the underlying logger.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        self.log(LogLevels.NOTICE, msg, *args, **kwargs)

    def process(self, msg, kwargs):
        """Process the message to append the prefix.

        Args:
            msg (str): Message to be prefixed.
            kwargs (Dict[str, Any]): Keyword args for the message.

        Returns:
            Tuple[str, Dict[str, Any]]

        """
        return self.prefix_template.format(prefix=self.prefix, msg=msg), kwargs

    def success(self, msg, *args, **kwargs):
        """Delegate a success call to the underlying logger.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        self.log(LogLevels.SUCCESS, msg, *args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        """Delegate a verbose call to the underlying logger.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        self.log(LogLevels.VERBOSE, msg, *args, **kwargs)


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

    def verbose(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity `VERBOSE`.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        """
        if self.isEnabledFor(LogLevels.VERBOSE):
            self._log(LogLevels.VERBOSE, msg, args, **kwargs)
