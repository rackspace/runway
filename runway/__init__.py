"""Set package version."""
import logging
import sys

from . import cfngin, variables
from ._logging import LogLevels, RunwayLogger  # noqa

if sys.version_info.minor < 8:
    # importlib.metadata is standard lib for python>=3.8, use backport
    from importlib_metadata import version, PackageNotFoundError
else:
    from importlib.metadata import version, PackageNotFoundError  # pylint: disable=E

logging.setLoggerClass(RunwayLogger)

sys.modules['stacker'] = cfngin  # shim to remove stacker dependency
sys.modules['stacker.variables'] = variables  # shim to support standard variables

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    __version__ = '0.0.0'
