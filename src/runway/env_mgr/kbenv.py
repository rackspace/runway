"""Kubectl version management."""
import logging
import os
import platform
import shutil
import sys
import tempfile

# Old pylint on py2.7 incorrectly flags these
from six.moves.urllib.request import urlretrieve  # noqa pylint: disable=import-error,line-too-long
from six.moves.urllib.error import URLError  # noqa pylint: disable=import-error,relative-import,line-too-long

from . import EnvManager, ensure_versions_dir_exists, handle_bin_download_error
from ..util import md5sum

LOGGER = logging.getLogger('runway')
KB_VERSION_FILENAME = '.kubectl-version'


# Branch and local variable count will go down when py2 support is dropped
def download_kb_release(version,  # noqa pylint: disable=too-many-locals,too-many-branches
                        versions_dir, kb_platform=None, arch=None):
    """Download kubectl and return path to it."""
    version_dir = os.path.join(versions_dir, version)

    if arch is None:
        arch = (
            os.environ.get('KBENV_ARCH') if os.environ.get('KBENV_ARCH')
            else 'amd64')

    if not kb_platform:
        if platform.system().startswith('Darwin'):
            kb_platform = 'darwin'
        elif platform.system().startswith('Windows') or (
                platform.system().startswith('MINGW64') or (
                    platform.system().startswith('MSYS_NT') or (
                        platform.system().startswith('CYGWIN_NT')))):
            kb_platform = 'windows'
        else:
            kb_platform = 'linux'

    download_dir = tempfile.mkdtemp()
    filename = 'kubectl.exe' if kb_platform == 'windows' else 'kubectl'
    kb_url = "https://storage.googleapis.com/kubernetes-release/release/%s/bin/%s/%s" % (version, kb_platform, arch)  # noqa pylint: disable=line-too-long

    try:
        for i in [filename, filename + '.md5']:
            urlretrieve(kb_url + '/' + i,
                        os.path.join(download_dir, i))
    # IOError in py2; URLError in 3+
    except (IOError, URLError) as exc:
        handle_bin_download_error(exc, 'kubectl')

    with open(os.path.join(download_dir, filename + '.md5'), 'r') as stream:
        kb_hash = stream.read().rstrip('\n')

    if kb_hash != md5sum(os.path.join(download_dir, filename)):
        LOGGER.error("Downloaded kubectl %s does not match md5 %s",
                     filename, kb_hash)
        sys.exit(1)

    os.mkdir(version_dir)
    shutil.move(os.path.join(download_dir, filename),
                os.path.join(version_dir, filename))
    shutil.rmtree(download_dir)
    os.chmod(  # ensure it is executable
        os.path.join(version_dir, filename),
        os.stat(os.path.join(version_dir,
                             filename)).st_mode | 0o0111
    )


def get_version_requested(path):
    """Return string listing requested kubectl version."""
    kb_version_path = os.path.join(path,
                                   KB_VERSION_FILENAME)
    if not os.path.isfile(kb_version_path):
        LOGGER.error("kubectl install attempted and no %s file present to "
                     "dictate the version. Please create it (e.g.  write "
                     "\"1.14.0\" (without quotes) to the file and try again",
                     KB_VERSION_FILENAME)
        sys.exit(1)
    with open(kb_version_path, 'r') as stream:
        ver = stream.read().rstrip()
    return ver


class KBEnvManager(EnvManager):  # pylint: disable=too-few-public-methods
    """kubectl version management.

    Designed to be compatible with https://github.com/alexppg/kbenv .
    """

    def __init__(self, path=None):
        """Initialize class."""
        super(KBEnvManager, self).__init__('kbenv', path)

    def install(self, version_requested=None):
        """Ensure kubectl is available."""
        versions_dir = ensure_versions_dir_exists(self.env_dir)

        if not version_requested:
            version_requested = get_version_requested(self.path)

        if not version_requested.startswith('v'):
            version_requested = 'v' + version_requested

        # Return early (i.e before reaching out to the internet) if the
        # matching version is already installed
        if os.path.isdir(os.path.join(versions_dir,
                                      version_requested)):
            LOGGER.info("kubectl version %s already installed; using "
                        "it...", version_requested)
            return os.path.join(versions_dir,
                                version_requested,
                                'kubectl') + self.command_suffix

        LOGGER.info("Downloading and using kubectl version %s ...",
                    version_requested)
        download_kb_release(version_requested, versions_dir)
        LOGGER.info("Downloaded kubectl %s successfully", version_requested)
        return os.path.join(versions_dir,
                            version_requested,
                            'kubectl') + self.command_suffix
