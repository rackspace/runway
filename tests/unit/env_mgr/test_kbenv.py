"""Test runway.env_mgr.kbenv."""
# pylint: disable=no-self-use
# pyright: basic, reportFunctionMemberAccess=none
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional, Tuple

import pytest

from runway.env_mgr.kbenv import KB_VERSION_FILENAME, KBEnvManager, VersionTuple

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
        assert list(KBEnvManager().list_installed()) == []

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("0.15.2", VersionTuple(0, 15, 2)),
            ("v0.15.2", VersionTuple(0, 15, 2)),
            ("0.13.0", VersionTuple(0, 13, 0)),
            ("v0.13.0", VersionTuple(0, 13, 0)),
            ("0.15.0-alpha.13", VersionTuple(0, 15, 0, "alpha", 13)),
            ("v0.15.0-alpha.13", VersionTuple(0, 15, 0, "alpha", 13)),
            ("0.15.0-beta", VersionTuple(0, 15, 0, "beta", None)),
            ("v0.15.0-beta", VersionTuple(0, 15, 0, "beta", None)),
            ("0.15.0-rc.1", VersionTuple(0, 15, 0, "rc", 1)),
            ("v0.15.0-rc.1", VersionTuple(0, 15, 0, "rc", 1)),
        ],
    )
    def test_parse_version_string(
        self, provided: str, expected: Optional[VersionTuple]
    ) -> None:
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
            KBEnvManager.parse_version_string("0.15")

    def test_set_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test set_version."""
        version = VersionTuple(1, 22, 0)
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
        get_version_from_file = mocker.patch.object(
            KBEnvManager, "get_version_from_file"
        )
        parse_version_string = mocker.patch.object(
            KBEnvManager, "parse_version_string", return_value="success"
        )
        obj = KBEnvManager(tmp_path)
        obj.current_version = "version"
        assert obj.version == "success"
        get_version_from_file.assert_not_called()
        parse_version_string.assert_called_once_with("version")

    def test_version_get_version_from_file(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
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
        assert (
            KBEnvManager(mod_path, overlay_path=overlay_path).version_file == expected
        )


class TestVersionTuple:
    """Test VersionTuple."""

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ((0, 15, 5), "v0.15.5"),
            ((0, 15, 5, "rc"), "v0.15.5-rc"),
            ((0, 15, 5, "rc", 3), "v0.15.5-rc.3"),
        ],
    )
    def test_str(self, provided: Tuple[Any, ...], expected: str) -> None:
        """Test __str__."""
        assert str(VersionTuple(*provided)) == expected
