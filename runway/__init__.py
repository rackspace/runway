"""Set package version."""

import logging
from importlib.metadata import PackageNotFoundError, version  # type: ignore

from ._logging import LogLevels, RunwayLogger  # noqa: F401

logging.setLoggerClass(RunwayLogger)

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"
