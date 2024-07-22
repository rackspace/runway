"""System Information."""

from __future__ import annotations

import os
import platform
import sys
from typing import Any, ClassVar, cast, final

from ..compat import cached_property


@final
class OsInfo:
    """Information about the operating system running on the current system."""

    __instance: ClassVar[OsInfo | None] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> OsInfo:
        """Create a new instance of class.

        This class is a singleton so it will always return the same instance.

        """
        if cls.__instance is None:
            cls.__instance = cast(OsInfo, super().__new__(cls, *args, **kwargs))
        return cls.__instance

    @cached_property
    def is_darwin(self) -> bool:
        """Operating system is Darwin."""
        return self.name == "darwin"

    @cached_property
    def is_linux(self) -> bool:
        """Operating system is Linux."""
        return self.name == "linux"

    @cached_property
    def is_macos(self) -> bool:
        """Operating system is macOS.

        Does not differentiate between macOS and Darwin.

        """
        return self.is_darwin

    @cached_property
    def is_posix(self) -> bool:
        """Operating system is posix."""
        return os.name == "posix"

    @cached_property
    def is_windows(self) -> bool:
        """Operating system is Windows."""
        return self.name == "windows"

    @cached_property
    def name(self) -> str:
        """Operating system name set to lowercase for consistency."""
        return platform.system().lower()

    @classmethod
    def clear_singleton(cls) -> None:
        """Clear singleton instances.

        Intended to only be used for running tests.

        """
        cls.__instance = None


@final
class SystemInfo:
    """Information about the system running Runway."""

    __instance: ClassVar[SystemInfo | None] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> SystemInfo:
        """Create a new instance of class.

        This class is a singleton so it will always return the same instance.

        """
        if cls.__instance is None:
            cls.__instance = cast(SystemInfo, super().__new__(cls, *args, **kwargs))
        return cls.__instance

    @cached_property
    def is_frozen(self) -> bool:
        """Whether or not Runway is running from a frozen package (Pyinstaller)."""
        return bool(getattr(sys, "frozen", False))

    @cached_property
    def os(self) -> OsInfo:
        """Operating system information."""
        return OsInfo()

    @classmethod
    def clear_singleton(cls) -> None:
        """Clear singleton instances.

        Intended to only be used for running tests.

        """
        cls.__instance = None
