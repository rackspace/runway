"""Set package version."""
import sys
from . import cfngin
from . import variables

sys.modules['stacker'] = cfngin  # shim to remove stacker dependency
sys.modules['stacker.variables'] = variables  # shim to support standard variables

__version__ = '1.4.1'
