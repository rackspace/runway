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

from .util import md5sum

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
        if sys.version_info[0] == 2:
            url_error_msg = str(exc.strerror)
        else:
            url_error_msg = str(exc.reason)

        if 'CERTIFICATE_VERIFY_FAILED' in url_error_msg:
            LOGGER.error('Attempted to download kubectl but was unable to '
                         'verify the TLS certificate on its download site.')
            LOGGER.error("Full TLS error message: %s", url_error_msg)
            if platform.system().startswith('Darwin') and (
                    'unable to get local issuer certificate' in url_error_msg):
                LOGGER.error("This is likely caused by your Python "
                             "installation missing root certificates. Run "
                             "\"/Applications/Python %s.%s/"
                             "\"Install Certificates.command\" to fix it "
                             "(https://stackoverflow.com/a/42334357/2547802)",
                             sys.version_info[0],
                             sys.version_info[1])
            sys.exit(1)
        else:
            raise

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


def ensure_versions_dir_exists(kbenv_path):
    """Ensure versions directory is available."""
    versions_dir = os.path.join(kbenv_path, 'versions')
    if not os.path.isdir(kbenv_path):
        os.mkdir(kbenv_path)
    if not os.path.isdir(versions_dir):
        os.mkdir(versions_dir)
    return versions_dir


class KBEnvManager(object):  # pylint: disable=too-few-public-methods
    """kubectl version management.

    Designed to be compatible with https://github.com/alexppg/kbenv .
    """

    def __init__(self, path=None):
        """Initialize class."""
        if path is None:
            self.path = os.getcwd()
        else:
            self.path = path

        if platform.system() == 'Windows':
            if 'APPDATA' in os.environ:
                self.kbenv_dir = os.path.join(os.environ['APPDATA'],
                                              'kbenv')
            else:
                for i in [['AppData'], ['AppData', 'Roaming']]:
                    if not os.path.isdir(os.path.join(os.path.expanduser('~'),
                                                      *i)):
                        os.mkdir(os.path.join(os.path.expanduser('~'),
                                              *i))
                self.kbenv_dir = os.path.join(os.path.expanduser('~'),
                                              'AppData',
                                              'Roaming',
                                              'kbenv')
        else:
            self.kbenv_dir = os.path.join(os.path.expanduser('~'),
                                          '.kbenv')

    def install(self, version_requested=None):
        """Ensure kubectl is available."""
        command_suffix = '.exe' if platform.system() == 'Windows' else ''
        versions_dir = ensure_versions_dir_exists(self.kbenv_dir)

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
                                'kubectl') + command_suffix

        LOGGER.info("Downloading and using kubectl version %s ...",
                    version_requested)
        download_kb_release(version_requested, versions_dir)
        LOGGER.info("Downloaded kubectl %s successfully", version_requested)
        return os.path.join(versions_dir, version_requested, 'kubectl') + command_suffix
