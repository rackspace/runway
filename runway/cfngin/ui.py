"""CFNgin UI manipulation."""

from __future__ import annotations

import logging
import threading
from contextlib import AbstractContextManager
from getpass import getpass
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

LOGGER = logging.getLogger(__name__)


def get_raw_input(message: str) -> str:
    """Just a wrapper for :func:`input` for testing purposes."""
    return input(message)


class UI(AbstractContextManager["UI"]):
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
        msg: Exception | str,
        *args: Any,
        logger: logging.Logger | logging.LoggerAdapter[Any] = LOGGER,
        **kwargs: Any,
    ) -> None:
        """Log the message if the current thread owns the underlying lock.

        Args:
            lvl: Log level.
            msg: String template or exception to use for the log record.
            logger: Specific logger to log to.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
        with self:
            return logger.log(lvl, msg, *args, **kwargs)

    def info(
        self,
        msg: str,
        *args: Any,
        logger: logging.Logger | logging.LoggerAdapter[Any] = LOGGER,
        **kwargs: Any,
    ) -> None:
        """Log the line if the current thread owns the underlying lock.

        Args:
            msg: String template or exception to use
                for the log record.
            logger: Specific logger to log to.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

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

    def getpass(self, prompt: str, stream: TextIO | None = None) -> str:
        """Wrap getpass to lock the UI."""
        with self:
            return getpass(prompt, stream)

    def __enter__(self) -> Self:
        """Enter the context manager."""
        self._lock.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager."""
        self._lock.__exit__(exc_type, exc_value, traceback)


# Global UI object for other modules to use.
ui = UI()
