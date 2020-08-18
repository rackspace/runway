"""Test runway.env_mgr."""
# pylint: disable=no-self-use,unused-argument
from mock import MagicMock

from runway.env_mgr import EnvManager


class TestEnvManager(object):
    """Test runway.env_mgr.EnvManager."""

    def test_bin(self, platform_darwin, cd_tmp_path, monkeypatch):
        """Test bin."""
        home = cd_tmp_path / "home"
        monkeypatch.setattr("runway.env_mgr.Path.home", MagicMock(return_value=home))
        obj = EnvManager("test-bin", "test-dir")
        obj.current_version = "1.0.0"

        assert obj.bin == home / ".test-dir" / "versions" / "1.0.0" / "test-bin"

    def test_darwin(self, platform_darwin, cd_tmp_path, monkeypatch):
        """Test init on Darwin platform."""
        home = cd_tmp_path / "home"
        monkeypatch.setattr("runway.env_mgr.Path.home", MagicMock(return_value=home))
        obj = EnvManager("test-bin", "test-dir")

        assert not obj.current_version
        assert obj.command_suffix == ""
        assert obj.env_dir_name == ".test-dir"
        assert obj.env_dir == home / ".test-dir"
        assert obj.versions_dir == home / ".test-dir" / "versions"

    def test_path(self, cd_tmp_path):
        """Test how path attribute is set."""
        assert EnvManager("", "", path=str(cd_tmp_path)).path == cd_tmp_path
        assert EnvManager("", "", path=cd_tmp_path).path == cd_tmp_path
        assert EnvManager("", "").path == cd_tmp_path

    def test_windows(self, platform_windows, cd_tmp_path, monkeypatch):
        """Test init on Windows platform."""
        home = cd_tmp_path / "home"
        monkeypatch.setattr("runway.env_mgr.Path.home", MagicMock(return_value=home))
        monkeypatch.delenv("APPDATA", raising=False)
        obj = EnvManager("test-bin", "test-dir")

        expected_env_dir = home / "AppData" / "Roaming" / "test-dir"

        assert not obj.current_version
        assert obj.command_suffix == ".exe"
        assert obj.env_dir_name == "test-dir"
        assert obj.env_dir == expected_env_dir
        assert obj.versions_dir == expected_env_dir / "versions"

    def test_windows_appdata(self, platform_windows, cd_tmp_path, monkeypatch):
        """Test init on Windows platform."""
        monkeypatch.setenv("APPDATA", str(cd_tmp_path / "custom_path"))
        obj = EnvManager("test-bin", "test-dir")

        expected_env_dir = cd_tmp_path / "custom_path" / "test-dir"

        assert not obj.current_version
        assert obj.command_suffix == ".exe"
        assert obj.env_dir_name == "test-dir"
        assert obj.env_dir == expected_env_dir
        assert obj.versions_dir == expected_env_dir / "versions"
