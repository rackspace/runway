"""Base module for environment managers."""
import logging
import os
import platform
import sys

from ..util import cached_property

if sys.version_info[0] > 2:  # TODO remove after droping python 2
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


def handle_bin_download_error(exc, name):
    """Give user info about their failed download."""
    if sys.version_info[0] == 2:
        url_error_msg = str(exc.strerror)
    else:
        url_error_msg = str(exc.reason)

    if "CERTIFICATE_VERIFY_FAILED" in url_error_msg:
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
    else:
        raise exc


class EnvManager(object):  # pylint: disable=too-few-public-methods
    """Base environment manager class.

    Attributes:
        bin (Optional[str]): Path to the binary of the current version.
        current_version (Optional[str]): The current binary
            version being used.
        env_dir_name (str): Name of the directory within the users home
            directory where binary versions will be stored.
        path (Path): The current working directory.

    """

    def __init__(self, bin_name, dir_name, path=None):
        """Initialize class.

        Args:
            bin_name (str): Name of the binary file (e.g. kubectl)
            dir_name (str): Name of the directory within the users home
                directory where binary versions will be stored.
            path (Optional[Path]): The current working directory.

        """
        self._bin_name = bin_name + self.command_suffix
        self.current_version = None
        self.env_dir_name = (
            dir_name if platform.system() == "Windows" else "." + dir_name
        )
        if not path:
            self.path = Path.cwd()
        elif not isinstance(path, Path):  # convert string to Path
            self.path = Path(path)
        else:
            self.path = path

    @property
    def bin(self):
        """Path to the version binary.

        Returns:
            Path

        """
        return self.versions_dir / self.current_version / self._bin_name

    @cached_property
    def command_suffix(self):  # pylint: disable=no-self-use
        """Return command suffix based on platform.system."""
        if platform.system() == "Windows":
            return ".exe"
        return ""

    @cached_property
    def env_dir(self):
        """Return the directory used to store version binaries."""
        if platform.system() == "Windows":
            if "APPDATA" in os.environ:
                return Path(os.environ["APPDATA"]) / self.env_dir_name
            return Path.home() / "AppData" / "Roaming" / self.env_dir_name
        return Path.home() / self.env_dir_name

    @cached_property
    def versions_dir(self):
        """Return the directory used to store binary.

        When first used, the existence of the directory is checked and it is
        created if needed.

        """
        return self.env_dir / "versions"
