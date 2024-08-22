"""Kubectl version management."""

from __future__ import annotations

import hashlib
import locale
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING, Final, cast
from urllib.error import URLError
from urllib.request import urlretrieve

import requests

from ..compat import cached_property
from ..exceptions import KubectlVersionNotSpecified
from ..utils import FileHash, Version
from . import EnvManager, handle_bin_download_error

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from .._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))
KB_VERSION_FILENAME = ".kubectl-version"
RELEASE_URI = "https://storage.googleapis.com/kubernetes-release/release"


def verify_kb_release(kb_url: str, download_dir: str, filename: str) -> None:
    """Compare checksum and exit if it doesn't match.

    Different releases provide varying checksum files. To account for this,
    start at SHA512 and work down to the first available checksum.

    requests is used for downloading these small files because of difficulty in
    getting 404 status from urllib on py2. Once py2 support is dropped, downloads
    can be moved to urllib.

    https://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve

    """
    # This might be a bit cleaner refactored as self-referencing function, but
    # the ridiculousness should be short-lived as md5 & sha1 support won't last
    # long.
    try:
        hash_alg: hashlib._Hash = hashlib.sha512()
        checksum_filename = filename + "." + hash_alg.name
        LOGGER.debug("attempting download of kubectl %s checksum...", hash_alg.name)
        download_request = requests.get(
            kb_url + "/" + checksum_filename, allow_redirects=True, timeout=30
        )
        download_request.raise_for_status()
    except requests.exceptions.HTTPError:
        try:
            hash_alg = hashlib.sha256()
            checksum_filename = filename + "." + hash_alg.name
            LOGGER.debug("attempting download of kubectl %s checksum...", hash_alg.name)
            download_request = requests.get(
                kb_url + "/" + checksum_filename, allow_redirects=True, timeout=30
            )
            download_request.raise_for_status()
        except requests.exceptions.HTTPError:
            try:
                hash_alg = hashlib.sha1()  # noqa: S324
                checksum_filename = filename + "." + hash_alg.name
                LOGGER.debug("attempting download of kubectl %s checksum...", hash_alg.name)
                download_request = requests.get(
                    kb_url + "/" + checksum_filename, allow_redirects=True, timeout=30
                )
                download_request.raise_for_status()
            except requests.exceptions.HTTPError:
                try:
                    hash_alg = hashlib.md5()  # noqa: S324
                    checksum_filename = filename + "." + hash_alg.name
                    LOGGER.debug("attempting download of kubectl %s checksum...", hash_alg.name)
                    download_request = requests.get(
                        kb_url + "/" + checksum_filename, allow_redirects=True, timeout=30
                    )
                    download_request.raise_for_status()
                except requests.exceptions.HTTPError:
                    LOGGER.error("Unable to retrieve kubectl checksum file")
                    sys.exit(1)

    kb_hash = download_request.content.decode().rstrip("\n")

    checksum = FileHash(hash_alg)
    checksum.add_file(os.path.join(download_dir, filename))  # noqa: PTH118
    if kb_hash != checksum.hexdigest:
        LOGGER.error(
            "downloaded kubectl %s does not match %s checksum %s",
            filename,
            hash_alg.name,
            kb_hash,
        )
        sys.exit(1)
    LOGGER.debug("kubectl matched %s checksum...", hash_alg.name)


def download_kb_release(
    version: str,
    versions_dir: Path,
    kb_platform: str | None = None,
    arch: str | None = None,
) -> None:
    """Download kubectl and return path to it."""
    version_dir = versions_dir / version

    if arch is None:
        arch = os.getenv("KBENV_ARCH", "amd64")

    if not kb_platform:
        if platform.system().startswith("Darwin"):
            kb_platform = "darwin"
        elif platform.system().startswith("Windows") or (
            platform.system().startswith("MINGW64")
            or (
                platform.system().startswith("MSYS_NT")
                or (platform.system().startswith("CYGWIN_NT"))
            )
        ):
            kb_platform = "windows"
        else:
            kb_platform = "linux"

    download_dir = tempfile.mkdtemp()
    filename = "kubectl.exe" if kb_platform == "windows" else "kubectl"
    kb_url = f"{RELEASE_URI}/{version}/bin/{kb_platform}/{arch}"

    try:
        LOGGER.verbose("downloading kubectl from %s...", kb_url)
        urlretrieve(  # noqa: S310
            kb_url + "/" + filename, os.path.join(download_dir, filename)  # noqa: PTH118
        )
    except URLError as exc:
        handle_bin_download_error(exc, "kubectl")

    verify_kb_release(kb_url, download_dir, filename)

    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(os.path.join(download_dir, filename), version_dir / filename)  # noqa: PTH118
    shutil.rmtree(download_dir)
    result = version_dir / filename
    result.chmod(result.stat().st_mode | 0o0111)  # ensure it is executable


class KBEnvManager(EnvManager):
    """kubectl version management.

    Designed to be compatible with https://github.com/alexppg/kbenv.

    """

    VERSION_REGEX: Final[str] = r"^(v)?(?P<version>[0-9]+\.[0-9]+\.[0-9]+\S*)"

    def __init__(self, path: Path | None = None, *, overlay_path: Path | None = None) -> None:
        """Initialize class.

        Args:
            path: Module path.
            overlay_path: Path to Kustomize overlay.

        """
        super().__init__("kubectl", "kbenv", path)
        self.overlay_path = overlay_path

    @cached_property
    def version(self) -> Version | None:
        """Terraform version."""
        if not self.current_version:
            self.current_version = self.get_version_from_file()
        if not self.current_version:
            return None
        return self.parse_version_string(self.current_version)

    @cached_property
    def version_file(self) -> Path | None:
        """Find and return a ".kubectl-version" file if one is present.

        Returns:
            Path to the kubectl version file.

        """
        path_list = [self.path, self.path.parent]
        if self.overlay_path:
            path_list.insert(0, self.overlay_path)
        for path in path_list:
            tmp_path = path / KB_VERSION_FILENAME
            if tmp_path.is_file():
                LOGGER.debug("using version file: %s", tmp_path)
                return tmp_path
        return None

    def get_version_from_file(self, file_path: Path | None = None) -> str | None:
        """Get kubectl version from a file.

        Args:
            file_path: Path to file that will be read.

        """
        file_path = file_path or self.version_file
        if file_path and file_path.is_file():
            return file_path.read_text(
                encoding=locale.getpreferredencoding(do_setlocale=False)
            ).strip()
        LOGGER.debug("file path not provided and version file could not be found")
        return None

    def install(self, version_requested: str | None = None) -> str:
        """Ensure kubectl is available."""
        if not version_requested:
            if self.version:
                version_requested = str(self.version)
            else:
                LOGGER.warning(
                    "kubectl version not specified and %s file not found",
                    KB_VERSION_FILENAME,
                )
                raise KubectlVersionNotSpecified

        if not version_requested.startswith("v"):
            version_requested = "v" + version_requested

        # Return early (i.e before reaching out to the internet) if the
        # matching version is already installed
        if (self.versions_dir / version_requested).is_dir():
            LOGGER.verbose("kubectl version %s already installed; using it...", version_requested)
            self.current_version = version_requested
            return str(self.bin)

        LOGGER.info("downloading and using kubectl version %s ...", version_requested)
        download_kb_release(version_requested, self.versions_dir)
        LOGGER.verbose("downloaded kubectl %s successfully", version_requested)
        self.current_version = version_requested
        return str(self.bin)

    def list_installed(self) -> Generator[Path, None, None]:
        """List installed versions of kubectl.

        Only lists versions of kubectl that have been installed by an instance
        if this class or by kbenv.

        """
        LOGGER.verbose("checking %s for kubectl versions...", self.versions_dir)
        return self.versions_dir.rglob("v*.*.*")

    def set_version(self, version: str) -> None:
        """Set current version.

        Clears cached values as needed.

        Args:
            version: Version string. Must be in the format of
                ``v<major>.<minor>.<patch>`` with an optional ``-<prerelease>``.

        """
        if self.current_version == version:
            return
        self.current_version = version
        self._del_cached_property("version")

    @classmethod
    def parse_version_string(cls, version: str) -> Version:
        """Parse version string into a :class:`Version`.

        Args:
            version: Version string to parse. Must be in the format of
                ``<major>.<minor>.<patch>`` with an optional ``-<prerelease>``.

        """
        match = re.search(cls.VERSION_REGEX, version)
        if not match:
            raise ValueError(f"provided version doesn't conform to regex: {cls.VERSION_REGEX}")
        return Version(f"v{match.group('version')}")
