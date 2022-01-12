"""Set package version."""
import logging
import sys

from ._logging import LogLevels, RunwayLogger  # noqa: F401

logging.setLoggerClass(RunwayLogger)

if sys.version_info < (3, 8):
    # importlib.metadata is standard lib for python>=3.8, use backport
    from importlib_metadata import PackageNotFoundError, version  # type: ignore
else:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"
