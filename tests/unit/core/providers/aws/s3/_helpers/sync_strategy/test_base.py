"""Test runway.core.providers.aws.s3._helpers.sync_strategy.base."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, List, Optional, cast

import pytest
from mock import Mock

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.sync_strategy.base import (
    BaseSync,
    MissingFileSync,
    NeverSync,
    SizeAndLastModifiedSync,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.sync_strategy.base import ValidSyncType

MODULE = "runway.core.providers.aws.s3._helpers.sync_strategy.base"


class TestBaseSync:
    """Test BaseSync."""

    @pytest.mark.parametrize(
        "src_size, dest_size, expected",
        [(10, 10, True), (10, 11, False), (11, 10, False)],
    )
    def test_compare_size(self, dest_size: int, expected: bool, src_size: int) -> None:
        """Test compare_size."""
        src_file = FileStats(src="", size=src_size)
        dest_file = FileStats(src="", size=dest_size)
        assert BaseSync.compare_size(src_file, dest_file) is expected

    @pytest.mark.parametrize(
        "src, dest", [(None, None), (Mock(), None), (None, Mock())]
    )
    def test_compare_size_raise_value_error(
        self, dest: Optional[FileStats], src: Optional[FileStats]
    ) -> None:
        """Test compare_time."""
        with pytest.raises(ValueError) as excinfo:
            BaseSync().compare_size(src, dest)
        assert str(excinfo.value) == "src_file and dest_file must not be None"

    def test_compare_time(self) -> None:
        """Test compare_time."""
        obj = BaseSync()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(0, 15)
        kwargs = {"src": "", "operation_name": "invalid"}
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is False
        )
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=future, **kwargs),
            )
            is False
        )
        assert (
            obj.compare_time(
                FileStats(last_update=future, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is False
        )

    @pytest.mark.parametrize("operation_name", ["copy", "upload"])
    def test_compare_time_copy_or_upload(self, operation_name: str) -> None:
        """Test compare_time."""
        obj = BaseSync()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(0, 15)
        kwargs = {"src": "", "operation_name": operation_name}
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is True
        )
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=future, **kwargs),
            )
            is True
        )
        assert (
            obj.compare_time(
                FileStats(last_update=future, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is False
        )

    def test_compare_time_download(self) -> None:
        """Test compare_time."""
        obj = BaseSync()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(0, 15)
        kwargs = {"src": "", "operation_name": "download"}
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is True
        )
        assert (
            obj.compare_time(
                FileStats(last_update=now, **kwargs),
                FileStats(last_update=future, **kwargs),
            )
            is False
        )
        assert (
            obj.compare_time(
                FileStats(last_update=future, **kwargs),
                FileStats(last_update=now, **kwargs),
            )
            is True
        )

    @pytest.mark.parametrize(
        "src, dest", [(None, None), (Mock(), None), (None, Mock())]
    )
    def test_compare_time_raise_value_error(
        self, dest: Optional[FileStats], src: Optional[FileStats]
    ) -> None:
        """Test compare_time."""
        with pytest.raises(ValueError) as excinfo:
            BaseSync().compare_time(src, dest)
        assert str(excinfo.value) == "src_file and dest_file must not be None"

    def test_determine_should_sync(self) -> None:
        """Test determine_should_sync."""
        with pytest.raises(NotImplementedError):
            BaseSync().determine_should_sync(None, None)  # type: ignore

    def test_init(self) -> None:
        """Test __init__."""
        valid_sync_types: List[ValidSyncType] = [
            "file_at_src_and_dest",
            "file_not_at_dest",
            "file_not_at_src",
        ]
        for sync_type in valid_sync_types:
            strategy = BaseSync(sync_type)
            assert strategy.sync_type == sync_type

        with pytest.raises(ValueError):
            BaseSync("invalid_sync_type")  # type: ignore

    def test_name(self) -> None:
        """Test name."""
        assert BaseSync().name is None

    def test_register_strategy(self) -> None:
        """Test register_strategy."""
        session = Mock()
        obj = BaseSync()
        obj.register_strategy(session)
        register_args = cast(Mock, session.register).call_args_list
        assert register_args[0][0][0] == "choosing-s3-sync-strategy"
        assert register_args[0][0][1] == obj.use_sync_strategy

    def test_use_sync_strategy(self, mocker: MockerFixture) -> None:
        """Test use_sync_strategy."""
        assert (
            BaseSync().use_sync_strategy(
                {"invalid_sync_strategy": True}  # type: ignore
            )
            is None
        )
        mocker.patch.object(BaseSync, "name", "something")
        obj = BaseSync()
        assert obj.use_sync_strategy({"something": True}) == obj  # type: ignore


class TestMissingFileSync:
    """Test MissingFileSync."""

    @pytest.mark.parametrize(
        "is_size, is_time, expected",
        [
            (True, True, True),
            (True, False, True),
            (False, True, True),
            (False, False, True),
        ],
    )
    def test_determine_should_sync(
        self, expected: bool, is_size: bool, is_time: bool, mocker: MockerFixture
    ) -> None:
        """Test determine_should_sync."""
        mock_compare_size = mocker.patch.object(
            MissingFileSync, "compare_size", return_value=is_size
        )
        mock_compare_time = mocker.patch.object(
            MissingFileSync, "compare_time", return_value=is_time
        )
        assert (
            MissingFileSync().determine_should_sync(
                FileStats(src=""), FileStats(src="")
            )
            is expected
        )
        mock_compare_size.assert_not_called()
        mock_compare_time.assert_not_called()

    def test_name(self) -> None:
        """Test name."""
        assert MissingFileSync().name is None

    def test_sync_type(self) -> None:
        """Test sync_type."""
        assert MissingFileSync().sync_type == "file_not_at_dest"


class TestTestNeverSync:
    """Test NeverSync."""

    @pytest.mark.parametrize(
        "is_size, is_time, expected",
        [
            (True, True, False),
            (True, False, False),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_determine_should_sync(
        self, expected: bool, is_size: bool, is_time: bool, mocker: MockerFixture
    ) -> None:
        """Test determine_should_sync."""
        mock_compare_size = mocker.patch.object(
            NeverSync, "compare_size", return_value=is_size
        )
        mock_compare_time = mocker.patch.object(
            NeverSync, "compare_time", return_value=is_time
        )
        assert (
            NeverSync().determine_should_sync(FileStats(src=""), FileStats(src=""))
            is expected
        )
        mock_compare_size.assert_not_called()
        mock_compare_time.assert_not_called()

    def test_name(self) -> None:
        """Test name."""
        assert NeverSync().name is None

    def test_sync_type(self) -> None:
        """Test sync_type."""
        assert NeverSync().sync_type == "file_not_at_src"


class TestSizeAndLastModifiedSync:
    """Test SizeAndLastModifiedSync."""

    @pytest.mark.parametrize(
        "is_size, is_time, expected",
        [
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (False, False, True),
        ],
    )
    def test_determine_should_sync(
        self, expected: bool, is_size: bool, is_time: bool, mocker: MockerFixture
    ) -> None:
        """Test determine_should_sync."""
        src_file = FileStats(src="")
        dest_file = FileStats(src="")
        mock_compare_size = mocker.patch.object(
            SizeAndLastModifiedSync, "compare_size", return_value=is_size
        )
        mock_compare_time = mocker.patch.object(
            SizeAndLastModifiedSync, "compare_time", return_value=is_time
        )
        assert (
            SizeAndLastModifiedSync().determine_should_sync(src_file, dest_file)
            is expected
        )
        mock_compare_size.assert_called_once_with(src_file, dest_file)
        mock_compare_time.assert_called_once_with(src_file, dest_file)

    def test_name(self) -> None:
        """Test name."""
        assert BaseSync().name is None
