"""Set package version."""
import sys
from . import cfngin

sys.modules['stacker'] = cfngin  # shim to remove stacker dependency

__version__ = '1.4.0'
