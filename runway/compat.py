"""Python dependency compatibility handling."""

import sys
from functools import cached_property
from importlib.metadata import PackageNotFoundError, version
from shlex import join as shlex_join

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

__all__ = [
    "PackageNotFoundError",  # TODO (kyle): remove in next major release
    "Self",
    "cached_property",  # TODO (kyle): remove in next major release
    "shlex_join",  # TODO (kyle): remove in next major release
    "version",  # TODO (kyle): remove in next major release
]
