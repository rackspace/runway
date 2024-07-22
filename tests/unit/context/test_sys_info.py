"""Test runway.context.sys_info."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.context.sys_info import OsInfo, SystemInfo

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.context.sys_info"


@pytest.fixture()
def clear_os_info() -> None:
    """Clear OsInfo singleton."""
    OsInfo.clear_singleton()


@pytest.fixture()
def clear_system_info() -> None:
    """Clear OsInfo singleton."""
    SystemInfo.clear_singleton()


@pytest.mark.usefixtures("clear_os_info")
class TestOsInfo:
    """Test OsInfo."""

    def test_is_darwin_false(self, platform_linux: None) -> None:  # noqa: ARG002
        """Test is_darwin False."""
        assert not OsInfo().is_darwin

    def test_is_darwin(self, platform_darwin: None) -> None:  # noqa: ARG002
        """Test is_darwin."""
        assert OsInfo().is_darwin

    def test_is_linux_false(self, platform_darwin: None) -> None:  # noqa: ARG002
        """Test is_linux False."""
        assert not OsInfo().is_linux

    def test_is_linux(self, platform_linux: None) -> None:  # noqa: ARG002
        """Test is_linux."""
        assert OsInfo().is_linux

    def test_is_macos_false(self, platform_linux: None) -> None:  # noqa: ARG002
        """Test is_macos False."""
        assert not OsInfo().is_macos

    def test_is_macos(self, platform_darwin: None) -> None:  # noqa: ARG002
        """Test is_macos."""
        assert OsInfo().is_macos

    def test_is_posix_false(self, mocker: MockerFixture) -> None:
        """Test is_posix False."""
        mock_os = mocker.patch(f"{MODULE}.os")
        mock_os.name = "nt"
        assert not OsInfo().is_posix

    def test_is_posix(self, mocker: MockerFixture) -> None:
        """Test is_posix."""
        mock_os = mocker.patch(f"{MODULE}.os")
        mock_os.name = "posix"
        assert OsInfo().is_posix

    def test_is_windows_false(self, platform_linux: None) -> None:  # noqa: ARG002
        """Test is_windows False."""
        assert not OsInfo().is_windows

    def test_is_windows(self, platform_windows: None) -> None:  # noqa: ARG002
        """Test is_windows."""
        assert OsInfo().is_windows

    def test_name_darwin(self, platform_darwin: None) -> None:  # noqa: ARG002
        """Test name darwin."""
        assert OsInfo().name == "darwin"

    def test_name_linux(self, platform_linux: None) -> None:  # noqa: ARG002
        """Test name linux."""
        assert OsInfo().name == "linux"

    def test_name_windows(self, platform_windows: None) -> None:  # noqa: ARG002
        """Test name windows."""
        assert OsInfo().name == "windows"

    def test_singleton(self) -> None:
        """Test singleton."""
        assert id(OsInfo()) == id(OsInfo())


@pytest.mark.usefixtures("clear_system_info")
class TestSystemInfo:
    """Test SystemInfo."""

    def test_is_frozen_false(self) -> None:
        """Test is_frozen False."""
        assert not SystemInfo().is_frozen

    def test_is_frozen(self, mocker: MockerFixture) -> None:
        """Test is_frozen."""
        mocker.patch(f"{MODULE}.sys.frozen", True, create=True)
        assert SystemInfo().is_frozen

    def test_os(self) -> None:
        """Test os."""
        assert isinstance(SystemInfo().os, OsInfo)

    def test_singleton(self) -> None:
        """Test singleton."""
        assert id(SystemInfo()) == id(SystemInfo())
