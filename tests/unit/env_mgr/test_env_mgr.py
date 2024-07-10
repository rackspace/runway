"""Test runway.env_mgr."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import pytest

from runway.env_mgr import EnvManager

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture, MonkeyPatch
    from pytest_mock import MockerFixture


class TestEnvManager:
    """Test runway.env_mgr.EnvManager."""

    def test___init___darwin(
        self, platform_darwin: None, cd_tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Test __init__ on Darwin platform."""
        home = cd_tmp_path / "home"
        mocker.patch("runway.env_mgr.Path.home", return_value=home)
        obj = EnvManager("test-bin", "test-dir")

        assert not obj.current_version
        assert obj.command_suffix == ""
        assert obj.env_dir_name == ".test-dir"
        assert obj.env_dir == home / ".test-dir"
        assert obj.versions_dir == home / ".test-dir" / "versions"

    def test___init___windows(
        self,
        platform_windows: None,
        cd_tmp_path: Path,
        mocker: MockerFixture,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test __init__ on Windows platform."""
        home = cd_tmp_path / "home"
        mocker.patch("runway.env_mgr.Path.home", return_value=home)
        monkeypatch.delenv("APPDATA", raising=False)
        obj = EnvManager("test-bin", "test-dir")

        expected_env_dir = home / "AppData" / "Roaming" / "test-dir"

        assert not obj.current_version
        assert obj.command_suffix == ".exe"
        assert obj.env_dir_name == "test-dir"
        assert obj.env_dir == expected_env_dir
        assert obj.versions_dir == expected_env_dir / "versions"

    def test___init___windows_appdata(
        self, platform_windows: None, cd_tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test __init__ on Windows platform."""
        monkeypatch.setenv("APPDATA", str(cd_tmp_path / "custom_path"))
        obj = EnvManager("test-bin", "test-dir")

        expected_env_dir = cd_tmp_path / "custom_path" / "test-dir"

        assert not obj.current_version
        assert obj.command_suffix == ".exe"
        assert obj.env_dir_name == "test-dir"
        assert obj.env_dir == expected_env_dir
        assert obj.versions_dir == expected_env_dir / "versions"

    def test_bin(self, platform_darwin: None, cd_tmp_path: Path, mocker: MockerFixture) -> None:
        """Test bin."""
        home = cd_tmp_path / "home"
        mocker.patch("runway.env_mgr.Path.home", return_value=home)
        obj = EnvManager("test-bin", "test-dir")
        obj.current_version = "1.0.0"

        assert obj.bin == home / ".test-dir" / "versions" / "1.0.0" / "test-bin"

    @pytest.mark.parametrize("version", ["1.0.0", None])
    def test_install(self, version: Optional[str]) -> None:
        """Test install."""
        with pytest.raises(NotImplementedError):
            assert EnvManager("", "").install(version)

    def test_list_installed(self) -> None:
        """Test list_installed."""
        with pytest.raises(NotImplementedError):
            assert EnvManager("", "").list_installed()

    def test_path(self, cd_tmp_path: Path) -> None:
        """Test how path attribute is set."""
        assert EnvManager("", "", path=cd_tmp_path).path == cd_tmp_path
        assert EnvManager("", "").path == cd_tmp_path

    @pytest.mark.parametrize("exists", [False, True])
    def test_uninstall(
        self,
        caplog: LogCaptureFixture,
        exists: bool,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test uninstall."""
        caplog.set_level(logging.INFO, logger="runway.env_mgr")
        mocker.patch.object(EnvManager, "versions_dir", tmp_path)
        obj = EnvManager("foo", "")
        version = "1.0.0"
        version_dir = tmp_path / version

        bin_name = "foo" + obj.command_suffix

        if exists:
            version_dir.mkdir()
            (version_dir / "foo").touch()
            assert obj.uninstall(version)
            assert f"uninstalling {bin_name} {version} from {tmp_path}..." in caplog.messages
            assert f"uninstalled {bin_name} {version}" in caplog.messages
        else:
            assert not obj.uninstall(version)
            assert f"{bin_name} {version} not installed" in caplog.messages

    def test_version_file(self) -> None:
        """Test version_file."""
        with pytest.raises(NotImplementedError):
            assert EnvManager("", "").version_file
