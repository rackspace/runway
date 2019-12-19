import unittest
from os import path

from runway.env_mgr.helmenv import (
    get_platform,
    get_binary_path,
    get_release_filename,
    get_release_url,
    get_version_requested
)


class ModulesHelmTestCase(unittest.TestCase):
    """Tests src/runway/env_mgr/helmenv.py."""

    def test_get_linux_platform(self):
        """Get platform should return linux."""
        os_platform = get_platform('Linux')
        self.assertEqual(os_platform, 'linux')

    def test_get_windows_platform(self):
        """Get platform should return windows."""
        os_platform = get_platform('Windows')
        self.assertEqual(os_platform, 'windows')

    def test_get_darwin_platform(self):
        """Get platform should return darwin."""
        os_platform = get_platform('Darwin')
        self.assertEqual(os_platform, 'darwin')

    def test_get_darwin_binary_path(self):
        """Get helm binary path should return the local path."""
        path = get_binary_path("/helm/3.0.0", "darwin", "amd64")
        self.assertEqual(path, '/helm/3.0.0/darwin-amd64/helm')

    def test_get_windows_binary_path(self):
        """Get helm binary path should return the local path."""
        path = get_binary_path("/helm/3.0.0", "windows", "amd64")
        self.assertEqual(path, '/helm/3.0.0/windows-amd64/helm.exe')

    def test_get_windows_release_filename(self):
        """Get windows release url."""
        filename = get_release_filename("3.0.0", "windows", "amd64")
        self.assertEqual(filename, 'helm-v3.0.0-windows-amd64.zip')

    def test_get_linux_release_filename(self):
        """Get linux release url."""
        filename = get_release_filename("3.0.0", "linux", "amd64")
        self.assertEqual(filename, 'helm-v3.0.0-linux-amd64.tar.gz')

    def test_get_release_filename(self):
        """Get release url."""
        filename = get_release_url("3.0.0", "linux", "amd64")
        self.assertEqual(filename, 'https://get.helm.sh/helm-v3.0.0-linux-amd64.tar.gz')

    def test_get_version_requested(self):
        """Get version requested."""
        folder = path.join(
            path.dirname(path.dirname(path.realpath(__file__))),
            "helm"
        )
        version = get_version_requested(folder)
        self.assertEqual(version, 'foo')
