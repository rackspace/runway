"""Helm management."""
import logging
import os
import platform
import shutil
import sys
import tempfile

# Old pylint on py2.7 incorrectly flags these
from six.moves.urllib.request import urlretrieve  # noqa pylint: disable=import-error,line-too-long

from . import EnvManager, ensure_versions_dir_exists
from ..util import sha256sum
from ..embedded.stacker.util import TarGzipExtractor, ZipExtractor

LOGGER = logging.getLogger('runway')
HELM_VERSION_FILENAME = '.helm-version'


def get_platform(os_platform):
    """Get the os platform."""
    if os_platform in ['Darwin', 'Linux', 'Windows']:
        return os_platform.lower()

    for prefix in ['Windows', 'WINGW64', 'MSYS_NT', 'CYGWIN_NT']:
        if os_platform.startswith(prefix):
            return 'windows'

    raise ValueError('Could not determine appropriate '
                     'OS platform for the download URL')


def decompress(source, target):
    """Decompress the given source file in the given target folder."""
    extractor_class = None
    if source.endswith('.tar.gz'):
        extractor_class = TarGzipExtractor
    elif source.endswith('.zip'):
        extractor_class = ZipExtractor
    else:
        raise Exception("unsupported file extension")
    extractor = extractor_class()
    suffix_length = -len(extractor_class.extension())
    extractor.set_archive(source[0:suffix_length])
    extractor.extract(target)


def get_binary_path(version_dir, os_platform, os_arch):
    """Get the binary path."""
    binary_name = 'helm.exe' if os_platform == 'windows' else 'helm'
    binary_file = "%s/%s-%s/%s" % (version_dir, os_platform, os_arch, binary_name)
    return binary_file


def get_release_filename(version_requested, os_platform, os_arch):
    """Get the compressed file name."""
    extension = "zip" if os_platform == "windows" else "tar.gz"
    filename = "helm-v%s-%s-%s.%s" % (version_requested, os_platform, os_arch, extension)
    return filename


def get_release_url(version_requested, os_platform, os_arch):
    """Get compressed file remote url."""
    filename = get_release_filename(version_requested, os_platform, os_arch)
    url = "https://get.helm.sh/%s" % (filename)
    return url


def download(version_dir, version_requested, os_platform, os_arch):
    """Download helm."""
    # Download release and hash
    release_filename = get_release_filename(version_requested, os_platform, os_arch)
    release_url = get_release_url(version_requested, os_platform, os_arch)
    LOGGER.info("Downloading Helm %s from %s", version_requested, release_url)

    download_dir = tempfile.mkdtemp()
    try:
        tmp_release_path = os.path.join(download_dir, release_filename)
        urlretrieve(release_url, tmp_release_path)
        release_hash_url = "%s.sha256" % (release_url)
        tmp_release_hash_path = os.path.join(download_dir, "hash")
        urlretrieve(release_hash_url, tmp_release_hash_path)

        # Validate hash
        actual_release_hash = sha256sum(tmp_release_path)
        with open(tmp_release_hash_path, 'r') as stream:
            expected_release_hash = stream.read().rstrip('\n')
        if actual_release_hash != expected_release_hash:
            LOGGER.error(
                "Downloaded helm %s does not match md5: %s != %s",
                release_filename,
                actual_release_hash,
                expected_release_hash)
            sys.exit(1)

        # Decompress release
        if not os.path.isdir(version_dir):
            os.mkdir(version_dir)
        decompress(tmp_release_path, version_dir)
        binary_file = get_binary_path(version_dir, os_platform, os_arch)
        os.chmod(binary_file, os.stat(binary_file).st_mode | 0o0111)
    finally:
        # Remove temporary folder
        shutil.rmtree(download_dir)


def get_version_requested(path):
    """Return string listing requested version."""
    helm_version_path = os.path.join(path,
                                     HELM_VERSION_FILENAME)
    if not os.path.isfile(helm_version_path):
        LOGGER.error("helm install attempted and no %s file present to "
                     "dictate the version. Please create it (e.g.  write "
                     "\"3.0.0\" (without quotes) to the file and try again",
                     HELM_VERSION_FILENAME)
        sys.exit(1)
    with open(helm_version_path, 'r') as stream:
        ver = stream.read().rstrip()
    return ver


class HelmEnvManager(EnvManager):  # pylint: disable=too-few-public-methods
    """Helm environment manager."""

    def __init__(self, path=None):
        """Initialize class."""
        super(HelmEnvManager, self).__init__('helm', path)

    def install(self, version_requested=None):
        """Ensure helm is available."""
        versions_dir = ensure_versions_dir_exists(self.env_dir)
        LOGGER.info("Checking Helm %s is available at %s", version_requested, versions_dir)

        # identify os platform and architecture
        os_arch = os.getenv('KBENV_ARCH', 'amd64')
        os_platform = get_platform(platform.system())

        # get binary path
        if not version_requested:
            version_requested = get_version_requested(self.path)
        version_dir = os.path.join(versions_dir, version_requested)
        binary_file = get_binary_path(version_dir, os_platform, os_arch)

        # dowload binary if not found locally
        if not os.path.isfile(binary_file):
            download(version_dir, version_requested, os_platform, os_arch)

        return binary_file
