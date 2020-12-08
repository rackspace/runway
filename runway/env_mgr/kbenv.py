"""Kubectl version management."""
import logging
import os
import platform
import shutil
import sys
import tempfile

import requests

# Old pylint on py2.7 incorrectly flags these
from six.moves.urllib.error import URLError  # pylint: disable=E
from six.moves.urllib.request import urlretrieve  # pylint: disable=E

from ..util import get_file_hash
from . import EnvManager, handle_bin_download_error

LOGGER = logging.getLogger(__name__)
KB_VERSION_FILENAME = ".kubectl-version"
RELEASE_URI = "https://storage.googleapis.com/kubernetes-release/release"


def verify_kb_release(kb_url, download_dir, filename):
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
        checksum_type = "sha512"
        checksum_filename = filename + "." + checksum_type
        LOGGER.debug("attempting download of kubectl %s checksum...", checksum_type)
        download_request = requests.get(
            kb_url + "/" + checksum_filename, allow_redirects=True
        )
        download_request.raise_for_status()
    except requests.exceptions.HTTPError:
        try:
            checksum_type = "sha256"
            checksum_filename = filename + "." + checksum_type
            LOGGER.debug("attempting download of kubectl %s checksum...", checksum_type)
            download_request = requests.get(
                kb_url + "/" + checksum_filename, allow_redirects=True
            )
            download_request.raise_for_status()
        except requests.exceptions.HTTPError:
            try:
                checksum_type = "sha1"
                checksum_filename = filename + "." + checksum_type
                LOGGER.debug(
                    "attempting download of kubectl %s checksum...", checksum_type
                )
                download_request = requests.get(
                    kb_url + "/" + checksum_filename, allow_redirects=True
                )
                download_request.raise_for_status()
            except requests.exceptions.HTTPError:
                try:
                    checksum_type = "md5"
                    checksum_filename = filename + "." + checksum_type
                    LOGGER.debug(
                        "attempting download of kubectl %s checksum...", checksum_type
                    )
                    download_request = requests.get(
                        kb_url + "/" + checksum_filename, allow_redirects=True
                    )
                    download_request.raise_for_status()
                except requests.exceptions.HTTPError:
                    LOGGER.error("Unable to retrieve kubectl checksum file")
                    sys.exit(1)

    if sys.version_info < (3, 0):
        kb_hash = download_request.content.rstrip("\n")
    else:
        kb_hash = download_request.content.decode().rstrip("\n")

    if kb_hash != get_file_hash(os.path.join(download_dir, filename), checksum_type):
        LOGGER.error(
            "downloaded kubectl %s does not match %s checksum %s",
            filename,
            checksum_type,
            kb_hash,
        )
        sys.exit(1)
    LOGGER.debug("kubectl matched %s checksum...", checksum_type)


def download_kb_release(
    version, versions_dir, kb_platform=None, arch=None,
):
    """Download kubectl and return path to it."""
    version_dir = versions_dir / version

    if arch is None:
        arch = os.environ.get("KBENV_ARCH") if os.environ.get("KBENV_ARCH") else "amd64"

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
    kb_url = "%s/%s/bin/%s/%s" % (RELEASE_URI, version, kb_platform, arch)

    try:
        LOGGER.verbose("downloading kubectl from %s...", kb_url)
        urlretrieve(kb_url + "/" + filename, os.path.join(download_dir, filename))
    # IOError in py2; URLError in 3+
    except (IOError, URLError) as exc:
        handle_bin_download_error(exc, "kubectl")

    verify_kb_release(kb_url, download_dir, filename)

    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(os.path.join(download_dir, filename), str(version_dir / filename))
    shutil.rmtree(download_dir)
    result = version_dir / filename
    result.chmod(result.stat().st_mode | 0o0111)  # ensure it is executable


def get_version_requested(path):
    """Return string listing requested kubectl version."""
    kb_version_path = path / KB_VERSION_FILENAME
    if not kb_version_path.is_file():
        LOGGER.error(
            "kubectl install attempted and no %s file present to "
            "dictate the version; please create it. (e.g. write "
            '"1.14.0", without quotes, to the file and try again)',
            KB_VERSION_FILENAME,
        )
        sys.exit(1)
    return kb_version_path.read_text().strip()


class KBEnvManager(EnvManager):  # pylint: disable=too-few-public-methods
    """kubectl version management.

    Designed to be compatible with https://github.com/alexppg/kbenv.

    """

    def __init__(self, path=None):
        """Initialize class."""
        super(KBEnvManager, self).__init__("kubectl", "kbenv", path)

    def install(self, version_requested=None):
        """Ensure kubectl is available."""
        if not version_requested:
            version_requested = get_version_requested(self.path)

        if not version_requested.startswith("v"):
            version_requested = "v" + version_requested

        # Return early (i.e before reaching out to the internet) if the
        # matching version is already installed
        if (self.versions_dir / version_requested).is_dir():
            LOGGER.verbose(
                "kubectl version %s already installed; using it...", version_requested,
            )
            self.current_version = version_requested
            return str(self.bin)

        LOGGER.info("downloading and using kubectl version %s ...", version_requested)
        download_kb_release(version_requested, self.versions_dir)
        LOGGER.verbose("downloaded kubectl %s successfully", version_requested)
        self.current_version = version_requested
        return str(self.bin)
