"""Python dependency compatability handling."""
# pylint: disable=E
import sys

if sys.version_info < (3, 8):  # 3.7
    from backports.cached_property import cached_property
    from importlib_metadata import PackageNotFoundError, version
else:
    from functools import cached_property
    from importlib.metadata import PackageNotFoundError, version

__all__ = ["cached_property", "PackageNotFoundError", "version"]
