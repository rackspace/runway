"""Test runway.env_mgr.kbenv."""

# pyright: reportFunctionMemberAccess=none
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from runway.env_mgr.kbenv import KB_VERSION_FILENAME, KBEnvManager
from runway.utils import Version

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

MODULE = "runway.env_mgr.kbenv"


class TestKBEnvManager:
    """Test KBEnvManager."""

    def test_get_version_from_file(self, tmp_path: Path) -> None:
        """Test get_version_from_file."""
        obj = KBEnvManager(tmp_path)

        # no version file or path
        assert not obj.get_version_from_file()

        # path not provided; use version file
        version_file = tmp_path / KB_VERSION_FILENAME
        version_file.write_text("v1.22.0")
        assert obj.get_version_from_file(version_file) == "v1.22.0"

    @pytest.mark.parametrize("version_requested", ["v1.21.0", "1.12.0"])
    def test_install_version_requested(
        self, mocker: MockerFixture, tmp_path: Path, version_requested: str
    ) -> None:
        """Test install version_requested."""
        mock_download_kb_release = mocker.patch(f"{MODULE}.download_kb_release")
        mocker.patch.object(KBEnvManager, "versions_dir", tmp_path / "kbenv")
        obj = KBEnvManager(tmp_path)
        assert obj.install(version_requested) == str(obj.bin)
        mock_download_kb_release.assert_called_once_with(
            (version_requested if version_requested.startswith("v") else f"v{version_requested}"),
            obj.versions_dir,
        )

    def test_list_installed(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test list_installed."""
        mocker.patch.object(KBEnvManager, "versions_dir", tmp_path)
        version_dirs = [tmp_path / "v1.14.0", tmp_path / "v1.21.0"]
        for v_dir in version_dirs:
            v_dir.mkdir()
        (tmp_path / "something.txt").touch()
        result = list(KBEnvManager().list_installed())  # convert generator to list
        result.sort()  # sort list for comparison
        assert result == version_dirs

    def test_list_installed_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test list_installed."""
        mocker.patch.object(KBEnvManager, "versions_dir", tmp_path)
        assert not list(KBEnvManager().list_installed())

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("0.15.2", Version("v0.15.2")),
            ("v0.15.2", Version("v0.15.2")),
            ("0.15.0-alpha.13", Version("v0.15.0-alpha.13")),
            ("v0.15.0-alpha.13", Version("v0.15.0-alpha.13")),
        ],
    )
    def test_parse_version_string(self, provided: str, expected: Version | None) -> None:
        """Test parse_version_string."""
        assert KBEnvManager.parse_version_string(provided) == expected

    def test_parse_version_string_raise_value_error(self) -> None:
        """Test parse_version_string."""
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"provided version doesn't conform to regex: {KBEnvManager.VERSION_REGEX}"
            ),
        ):
            KBEnvManager.parse_version_string("invalid")

    def test_set_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test set_version."""
        version = Version("1.22.0")
        mocker.patch.object(KBEnvManager, "get_version_from_file", return_value=None)
        obj = KBEnvManager(tmp_path)
        assert not obj.current_version
        assert not obj.set_version(str(version))
        assert obj.version == version
        assert obj.current_version == str(version)

    def test_set_version_same(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test set_version same."""
        version = mocker.patch.object(KBEnvManager, "version")
        obj = KBEnvManager(tmp_path)
        obj.current_version = "v1.22.0"
        assert not obj.set_version("v1.22.0")
        assert obj.current_version == "v1.22.0"
        assert obj.version == version

    def test_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version."""
        get_version_from_file = mocker.patch.object(KBEnvManager, "get_version_from_file")
        parse_version_string = mocker.patch.object(
            KBEnvManager, "parse_version_string", return_value="success"
        )
        obj = KBEnvManager(tmp_path)
        obj.current_version = "version"
        assert obj.version == "success"
        get_version_from_file.assert_not_called()
        parse_version_string.assert_called_once_with("version")

    def test_version_get_version_from_file(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version."""
        get_version_from_file = mocker.patch.object(
            KBEnvManager, "get_version_from_file", return_value="version"
        )
        parse_version_string = mocker.patch.object(
            KBEnvManager, "parse_version_string", return_value="success"
        )
        obj = KBEnvManager(tmp_path)
        assert obj.version == "success"
        get_version_from_file.assert_called_once_with()
        parse_version_string.assert_called_once_with("version")

    def test_version_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version."""
        get_version_from_file = mocker.patch.object(
            KBEnvManager, "get_version_from_file", return_value=None
        )
        parse_version_string = mocker.patch.object(KBEnvManager, "parse_version_string")
        obj = KBEnvManager(tmp_path)
        assert not obj.version
        get_version_from_file.assert_called_once_with()
        parse_version_string.assert_not_called()

    def test_version_file(self, tmp_path: Path) -> None:
        """Test version_file."""
        mod_path = tmp_path / "mod"
        overlay_path = mod_path / "overlay"
        overlay_path.mkdir(parents=True)
        obj = KBEnvManager(mod_path)

        # no version file
        assert not obj.version_file
        del obj.version_file

        # version file in parent dir
        expected = tmp_path / KB_VERSION_FILENAME
        expected.touch()
        assert obj.version_file == expected
        del obj.version_file

        # version file in module dir
        expected = mod_path / KB_VERSION_FILENAME
        expected.touch()
        assert obj.version_file == expected
        del obj.version_file

        # version file in overlay dir
        expected = overlay_path / KB_VERSION_FILENAME
        expected.touch()
        assert obj.version_file == mod_path / KB_VERSION_FILENAME
        assert KBEnvManager(mod_path, overlay_path=overlay_path).version_file == expected
