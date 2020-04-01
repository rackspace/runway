"""Import modules."""
from .cfngin import CFNgin  # noqa: F401

__all__ = ['CFNgin']

# added for stacker shim backward compatability.
# use of __version__ is deprecated and will be removed in 2.0.0.
__version__ = '1.7.0'
