"""CFNgin UI manipulation."""
from __future__ import annotations

import logging
import threading
from getpass import getpass
from typing import TYPE_CHECKING, Any, ContextManager, Optional, TextIO, Type, Union

if TYPE_CHECKING:
    from types import TracebackType

LOGGER = logging.getLogger(__name__)


def get_raw_input(message: str) -> str:
    """Just a wrapper for :func:`input` for testing purposes."""
    return input(message)


class UI(ContextManager["UI"]):
    """Used internally from terminal output in a multithreaded environment.

    Ensures that two threads don't write over each other while asking a user
    for input (e.g. in interactive mode).

    """

    def __init__(self) -> None:
        """Instantiate class."""
        self._lock = threading.RLock()

    def log(
        self,
        lvl: int,
        msg: Union[Exception, str],
        *args: Any,
        logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
        **kwargs: Any,
    ) -> None:
        """Log the message if the current thread owns the underlying lock.

        Args:
            lvl: Log level.
            msg: String template or exception to use for the log record.
            logger: Specific logger to log to.

        """
        with self:
            return logger.log(lvl, msg, *args, **kwargs)

    def info(
        self,
        msg: str,
        *args: Any,
        logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
        **kwargs: Any,
    ) -> None:
        """Log the line if the current thread owns the underlying lock.

        Args:
            msg: String template or exception to use
                for the log record.
            logger: Specific logger to log to.

        """
        kwargs["logger"] = logger
        self.log(logging.INFO, msg, *args, **kwargs)

    def ask(self, message: str) -> str:
        """Collect input from a user in a multithreaded environment.

        This wraps the built-in input function to ensure that only 1
        thread is asking for input from the user at a give time. Any process
        that tries to log output to the terminal will be blocked while the
        user is being prompted.

        """
        with self:
            return get_raw_input(message)

    def getpass(self, prompt: str, stream: Optional[TextIO] = None) -> str:
        """Wrap getpass to lock the UI."""
        with self:
            return getpass(prompt, stream)

    def __enter__(self) -> UI:
        """Enter the context manager."""
        self._lock.__enter__()  # pylint: disable=consider-using-with
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit the context manager."""
        self._lock.__exit__(exc_type, exc_value, traceback)


# Global UI object for other modules to use.
ui = UI()
