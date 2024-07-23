"""Test runway.core.providers.aws.s3._helpers.sync_strategy.size_only."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.sync_strategy.size_only import SizeOnlySync

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.aws.s3._helpers.sync_strategy.size_only"


class TestSizeOnlySync:
    """Test SizeOnlySync."""

    @pytest.mark.parametrize(
        "is_size, is_time, expected",
        [
            (True, True, False),
            (True, False, False),
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
        mock_compare_size = mocker.patch.object(SizeOnlySync, "compare_size", return_value=is_size)
        mock_compare_time = mocker.patch.object(SizeOnlySync, "compare_time", return_value=is_time)
        assert SizeOnlySync().determine_should_sync(src_file, dest_file) is expected
        mock_compare_size.assert_called_once_with(src_file, dest_file)
        mock_compare_time.assert_not_called()

    def test_name(self) -> None:
        """Test name."""
        assert SizeOnlySync().name == "size_only"
