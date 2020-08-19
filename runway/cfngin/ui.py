"""CFNgin UI manipulation."""
import logging
import threading
from getpass import getpass

from six.moves import input

LOGGER = logging.getLogger(__name__)


def get_raw_input(message):
    """Just a wrapper for :func:`input` for testing purposes."""
    return input(message)


class UI(object):
    """Used internally from terminal output in a multithreaded environment.

    Ensures that two threads don't write over each other while asking a user
    for input (e.g. in interactive mode).

    """

    def __init__(self):
        """Instantiate class."""
        self._lock = threading.RLock()

    def lock(self, *_args, **_kwargs):
        """Obtain an exclusive lock on the UI for the current thread."""
        return self._lock.acquire()

    # TODO uncomment signature when dropping python 2
    # def log(self, lvl, msg, *args, logger=LOGGER, **kwargs):
    def log(self, lvl, msg, *args, **kwargs):
        """Log the message if the current thread owns the underlying lock.

        Args:
            lvl (int): Log level.
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        Keyword Args:
            logger (Union[logging.LoggerAdaptor, logging.Logger]): Specific
                logger to log to.

        """
        self.lock()
        logger = kwargs.pop("logger", LOGGER)
        try:
            return logger.log(lvl, msg, *args, **kwargs)
        finally:
            self.unlock()

    def unlock(self, *_args, **_kwargs):
        """Release the lock on the UI."""
        return self._lock.release()

    # TODO uncomment signature when dropping python 2
    # def info(self, msg, *args, logger=LOGGER, **kwargs):
    def info(self, msg, *args, **kwargs):
        """Log the line if the current thread owns the underlying lock.

        Args:
            msg (Union[str, Exception]): String template or exception to use
                for the log record.

        Keyword Args:
            logger (Union[logging.LoggerAdaptor, logging.Logger]): Specific
                logger to log to.

        """
        self.log(logging.INFO, msg, *args, **kwargs)

    def ask(self, message):
        """Collect input from a user in a multithreaded environment.

        This wraps the built-in raw_input function to ensure that only 1
        thread is asking for input from the user at a give time. Any process
        that tries to log output to the terminal will be blocked while the
        user is being prompted.

        """
        self.lock()
        try:
            return get_raw_input(message)
        finally:
            self.unlock()

    def getpass(self, *args):
        """Wrap getpass to lock the UI."""
        try:
            self.lock()
            return getpass(*args)
        finally:
            self.unlock()


# Global UI object for other modules to use.
ui = UI()
