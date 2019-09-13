"""Base module for environment managers."""
import logging
import os
import platform
import sys

LOGGER = logging.getLogger('runway')


def ensure_versions_dir_exists(env_path):
    """Ensure versions directory is available."""
    versions_dir = os.path.join(env_path, 'versions')
    if not os.path.isdir(env_path):
        os.mkdir(env_path)
    if not os.path.isdir(versions_dir):
        os.mkdir(versions_dir)
    return versions_dir


def handle_bin_download_error(exc, name):
    """Give user info about their failed download."""
    if sys.version_info[0] == 2:
        url_error_msg = str(exc.strerror)
    else:
        url_error_msg = str(exc.reason)

    if 'CERTIFICATE_VERIFY_FAILED' in url_error_msg:
        LOGGER.error('Attempted to download %s but was unable to '
                     'verify the TLS certificate on its download site.',
                     name)
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
        raise exc


class EnvManager(object):  # pylint: disable=too-few-public-methods
    """Base environment manager class."""

    def __init__(self, dir_name, path=None):
        """Initialize class."""
        if path is None:
            self.path = os.getcwd()
        else:
            self.path = path

        if platform.system() == 'Windows':
            self.command_suffix = '.exe'
            if 'APPDATA' in os.environ:
                self.env_dir = os.path.join(os.environ['APPDATA'],
                                            dir_name)
            else:
                for i in [['AppData'], ['AppData', 'Roaming']]:
                    if not os.path.isdir(os.path.join(os.path.expanduser('~'),
                                                      *i)):
                        os.mkdir(os.path.join(os.path.expanduser('~'),
                                              *i))
                self.env_dir = os.path.join(os.path.expanduser('~'),
                                            'AppData',
                                            'Roaming',
                                            dir_name)
        else:
            self.command_suffix = ''
            self.env_dir = os.path.join(os.path.expanduser('~'),
                                        '.' + dir_name)
