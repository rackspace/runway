"""Base module for environment managers."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional, Tuple, Union, cast

from ..compat import cached_property

if TYPE_CHECKING:
    from urllib.error import URLError

    from runway._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def handle_bin_download_error(exc: URLError, name: str) -> None:
    """Give user info about their failed download.

    Raises:
        SystemExit: Always raised after logging reason.

    """
    url_error_msg = str(exc.reason)

    if "CERTIFICATE_VERIFY_FAILED" not in url_error_msg:
        raise exc

    LOGGER.error(
        "Attempted to download %s but was unable to verify the TLS "
        "certificate on its download site.",
        name,
    )
    LOGGER.error("Full TLS error message: %s", url_error_msg)
    if platform.system().startswith("Darwin") and (
        "unable to get local issuer certificate" in url_error_msg
    ):
        LOGGER.error(
            "This is likely caused by your Python installation missing root certificates. "
            'Run "/Applications/Python %s.%s/"Install Certificates.command" to fix it '
            "(https://stackoverflow.com/a/42334357/2547802)",
            sys.version_info[0],
            sys.version_info[1],
        )
    sys.exit(1)


class EnvManager:
    """Base environment manager class.

    Attributes:
        binPath to the binary of the current version.
        current_version: The current binary version being used.
        env_dir_name: Name of the directory within the users home
            directory where binary versions will be stored.
        path: The current working directory.

    """

    _bin_name: str

    current_version: Optional[str]
    env_dir_name: str
    path: Path

    def __init__(
        self, bin_name: str, dir_name: str, path: Optional[Path] = None
    ) -> None:
        """Initialize class.

        Args:
            bin_name: Name of the binary file (e.g. kubectl)
            dir_name: Name of the directory within the users home
                directory where binary versions will be stored.
            path: The current working directory.

        """
        self._bin_name = bin_name + self.command_suffix
        self.current_version = None
        self.env_dir_name = (
            dir_name if platform.system() == "Windows" else "." + dir_name
        )
        self.path = Path.cwd() if not path else path

    @property
    def bin(self) -> Path:
        """Path to the version binary.

        Returns:
            Path

        """
        if self.current_version:
            return self.versions_dir / self.current_version / self._bin_name
        return self.versions_dir / self._bin_name

    @cached_property
    def command_suffix(self) -> str:  # pylint: disable=no-self-use
        """Return command suffix based on platform.system."""
        if platform.system() == "Windows":
            return ".exe"
        return ""

    @cached_property
    def env_dir(self) -> Path:
        """Return the directory used to store version binaries."""
        if platform.system() == "Windows":
            if "APPDATA" in os.environ:
                return Path(os.environ["APPDATA"]) / self.env_dir_name
            return Path.home() / "AppData" / "Roaming" / self.env_dir_name
        return Path.home() / self.env_dir_name

    @cached_property
    def versions_dir(self) -> Path:
        """Return the directory used to store binary.

        When first used, the existence of the directory is checked and it is
        created if needed.

        """
        return self.env_dir / "versions"

    @cached_property
    def version_file(self) -> Optional[Path]:
        """Find and return a "<bin version file>" file if one is present.

        Returns:
            Path to the <bin> version file.

        """
        raise NotImplementedError

    def install(self, version_requested: Optional[str] = None) -> str:
        """Ensure <bin> is installed."""
        raise NotImplementedError

    def list_installed(self) -> Generator[Path, None, None]:
        """List installed versions of <bin>."""
        raise NotImplementedError

    def uninstall(self, version: Union[str, Tuple[Any, ...]]) -> bool:
        """Uninstall a version of the managed binary.

        Args:
            version: Version of binary to uninstall.

        Returns:
            Whether a version of the binary was uninstalled or not.

        """
        version_dir = self.versions_dir / str(version)
        if version_dir.is_dir():
            LOGGER.notice(
                "uninstalling %s %s from %s...",
                self._bin_name,
                version,
                self.versions_dir,
            )
            shutil.rmtree(version_dir)
            LOGGER.success("uninstalled %s %s", self._bin_name, version)
            return True
        LOGGER.error("%s %s not installed", self._bin_name, version)
        return False
