"""Set package version."""
# pylint: disable=wrong-import-position
import logging
import sys

from ._logging import LogLevels, RunwayLogger  # noqa  isort:skip

logging.setLoggerClass(RunwayLogger)  # isort:skip

# these need to be imported after setting the logger class
from . import cfngin, variables  # noqa isort:skip

if sys.version_info.minor < 8:
    # importlib.metadata is standard lib for python>=3.8, use backport
    from importlib_metadata import PackageNotFoundError, version
else:
    from importlib.metadata import PackageNotFoundError, version  # pylint: disable=E

sys.modules["stacker"] = cfngin  # shim to remove stacker dependency
sys.modules["stacker.variables"] = variables  # shim to support standard variables

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"
