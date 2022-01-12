"""Python dependency compatability handling."""
import sys
from typing import Iterable

if sys.version_info < (3, 8):  # 3.7
    import shlex

    from backports.cached_property import cached_property
    from importlib_metadata import PackageNotFoundError, version

    def shlex_join(split_command: Iterable[str]) -> str:
        """Backport of :meth:`shlex.join`."""
        return " ".join(shlex.quote(arg) for arg in split_command)

else:
    from functools import cached_property
    from importlib.metadata import PackageNotFoundError, version
    from shlex import join as shlex_join

__all__ = [
    "PackageNotFoundError",
    "cached_property",
    "shlex_join",
    "version",
]
