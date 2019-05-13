"""Terraform version management."""
from distutils.version import LooseVersion  # noqa pylint: disable=import-error,no-name-in-module
import glob
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import zipfile

# Old pylint on py2.7 incorrectly flags these
from six.moves.urllib.request import urlretrieve  # noqa pylint: disable=import-error,line-too-long
from six.moves.urllib.error import URLError  # noqa pylint: disable=import-error,relative-import,line-too-long

from botocore.vendored import requests
import hcl

from .util import get_hash_for_filename, sha256sum

LOGGER = logging.getLogger('runway')
TF_VERSION_FILENAME = '.terraform-version'


# Branch and local variable count will go down when py2 support is dropped
def download_tf_release(version,  # noqa pylint: disable=too-many-locals,too-many-branches
                        versions_dir, command_suffix, tf_platform=None,
                        arch=None):
    """Download Terraform archive and return path to it."""
    version_dir = os.path.join(versions_dir, version)

    if arch is None:
        arch = (
            os.environ.get('TFENV_ARCH') if os.environ.get('TFENV_ARCH')
            else 'amd64')

    if tf_platform:
        tfver_os = tf_platform + '_' + arch
    else:
        if platform.system().startswith('Darwin'):
            tfver_os = "darwin_%s" % arch
        elif platform.system().startswith('Windows') or (
                platform.system().startswith('MINGW64') or (
                    platform.system().startswith('MSYS_NT') or (
                        platform.system().startswith('CYGWIN_NT')))):
            tfver_os = "windows_%s" % arch
        else:
            tfver_os = "linux_%s" % arch

    download_dir = tempfile.mkdtemp()
    filename = "terraform_%s_%s.zip" % (version, tfver_os)
    shasums_name = "terraform_%s_SHA256SUMS" % version
    tf_url = "https://releases.hashicorp.com/terraform/" + version

    try:
        for i in [filename, shasums_name]:
            urlretrieve(tf_url + '/' + i,
                        os.path.join(download_dir, i))
    # IOError in py2; URLError in 3+
    except (IOError, URLError) as exc:
        if sys.version_info[0] == 2:
            url_error_msg = str(exc.strerror)
        else:
            url_error_msg = str(exc.reason)

        if 'CERTIFICATE_VERIFY_FAILED' in url_error_msg:
            LOGGER.error('Attempted to download Terraform but was unable to '
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

    tf_hash = get_hash_for_filename(filename, os.path.join(download_dir,
                                                           shasums_name))
    if tf_hash != sha256sum(os.path.join(download_dir, filename)):
        LOGGER.error("Downloaded Terraform %s does not match sha256 %s",
                     filename, tf_hash)
        sys.exit(1)

    tf_zipfile = zipfile.ZipFile(os.path.join(download_dir, filename))
    os.mkdir(version_dir)
    tf_zipfile.extractall(version_dir)
    tf_zipfile.close()
    shutil.rmtree(download_dir)
    os.chmod(  # ensure it is executable
        os.path.join(version_dir,
                     'terraform' + command_suffix),
        os.stat(os.path.join(version_dir,
                             'terraform' + command_suffix)).st_mode | 0o0111
    )


def get_available_tf_versions(include_prerelease=False):
    """Return available Terraform versions."""
    tf_releases = json.loads(
        requests.get('https://releases.hashicorp.com/index.json').text
    )['terraform']
    tf_versions = sorted([k  # descending
                          for k, _v in tf_releases['versions'].items()],
                         key=LooseVersion,
                         reverse=True)
    if include_prerelease:
        return tf_versions
    return [i for i in tf_versions if '-' not in i]


def get_latest_tf_version(include_prerelease=False):
    """Return latest Terraform version."""
    return get_available_tf_versions(include_prerelease)[0]


def find_min_required(path):
    """Inspect terraform files and find minimum version."""
    found_min_required = ''
    for filename in glob.glob(os.path.join(path, '*.tf')):
        with open(filename, 'r') as stream:
            tf_config = hcl.load(stream)
            if tf_config.get('terraform', {}).get('required_version'):
                found_min_required = tf_config.get('terraform',
                                                   {}).get('required_version')
                break

    if found_min_required:
        if re.match(r'^!=.+', found_min_required):
            LOGGER.error('Min required Terraform version is a negation (%s) '
                         '- unable to determine required version',
                         found_min_required)
            sys.exit(1)
        else:
            found_min_required = re.search(r'[0-9]*\.[0-9]*(?:\.[0-9]*)?',
                                           found_min_required).group(0)
            LOGGER.debug("Detected minimum terraform version is %s",
                         found_min_required)
            return found_min_required
    LOGGER.error('Terraform version specified as min-required, but unable to '
                 'find a specified version requirement in this module\'s tf '
                 'files')
    sys.exit(1)


def get_version_requested(path):
    """Return string listing requested Terraform version."""
    tf_version_path = os.path.join(path,
                                   TF_VERSION_FILENAME)
    if not os.path.isfile(tf_version_path):
        LOGGER.error("Terraform install attempted and no %s file present to "
                     "dictate the version. Please create it (e.g.  write "
                     "\"0.11.13\" (without quotes) to the file and try again",
                     TF_VERSION_FILENAME)
        sys.exit(1)
    with open(tf_version_path, 'r') as stream:
        ver = stream.read().rstrip()
    return ver


def ensure_versions_dir_exists(tfenv_path):
    """Ensure versions directory is available."""
    versions_dir = os.path.join(tfenv_path, 'versions')
    if not os.path.isdir(tfenv_path):
        os.mkdir(tfenv_path)
    if not os.path.isdir(versions_dir):
        os.mkdir(versions_dir)
    return versions_dir


class TFEnv(object):  # pylint: disable=too-few-public-methods
    """Terraform version management.

    Designed to be compatible with https://github.com/tfutils/tfenv .
    """

    def __init__(self, path=None):
        """Initialize class."""
        if path is None:
            self.path = os.getcwd()
        else:
            self.path = path

        if platform.system() == 'Windows':
            if 'APPDATA' in os.environ:
                self.tfenv_dir = os.path.join(os.environ['APPDATA'],
                                              'tfenv')
            else:
                for i in [['AppData'], ['AppData', 'Roaming']]:
                    if not os.path.isdir(os.path.join(os.path.expanduser('~'),
                                                      *i)):
                        os.mkdir(os.path.join(os.path.expanduser('~'),
                                              *i))
                self.tfenv_dir = os.path.join(os.path.expanduser('~'),
                                              'AppData',
                                              'Roaming',
                                              'tfenv')
        else:
            self.tfenv_dir = os.path.join(os.path.expanduser('~'),
                                          '.tfenv')

    def install(self, version_requested=None):
        """Ensure terraform is available."""
        command_suffix = '.exe' if platform.system() == 'Windows' else ''
        versions_dir = ensure_versions_dir_exists(self.tfenv_dir)

        if not version_requested:
            version_requested = get_version_requested(self.path)

        if re.match(r'^min-required$', version_requested):
            LOGGER.debug('tfenv: detecting minimal required version')
            version_requested = find_min_required(self.path)

        if re.match(r'^latest:.*$', version_requested):
            regex = re.search(r'latest:(.*)', version_requested).group(1)
            include_prerelease_versions = False
        elif re.match(r'^latest$', version_requested):
            regex = r'^[0-9]+\.[0-9]+\.[0-9]+$'
            include_prerelease_versions = False
        else:
            regex = "^%s$" % version_requested
            include_prerelease_versions = True
            # Return early (i.e before reaching out to the internet) if the
            # matching version is already installed
            if os.path.isdir(os.path.join(versions_dir,
                                          version_requested)):
                LOGGER.info("Terraform version %s already installed; using "
                            "it...", version_requested)
                return os.path.join(versions_dir,
                                    version_requested,
                                    'terraform') + command_suffix

        try:
            version = next(i
                           for i in get_available_tf_versions(
                               include_prerelease_versions)
                           if re.match(regex, i))
        except StopIteration:
            LOGGER.error("Unable to find a Terraform version matching regex: %s",
                         regex)
            sys.exit(1)

        # Now that a version has been selected, skip downloading if it's
        # already been downloaded
        if os.path.isdir(os.path.join(versions_dir,
                                      version)):
            LOGGER.info("Terraform version %s already installed; using it...",
                        version)
            return os.path.join(versions_dir,
                                version,
                                'terraform') + command_suffix

        LOGGER.info("Downloading and using Terraform version %s ...",
                    version)
        download_tf_release(version, versions_dir, command_suffix)
        LOGGER.info("Downloaded Terraform %s successfully", version)
        return os.path.join(versions_dir, version, 'terraform') + command_suffix
