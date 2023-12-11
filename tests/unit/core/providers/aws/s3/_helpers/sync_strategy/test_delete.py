"""Test runway.core.providers.aws.s3._helpers.sync_strategy.delete."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.sync_strategy.delete import DeleteSync

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.aws.s3._helpers.sync_strategy.delete"


class TestDeleteSync:
    """Test DeleteSync."""

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
            DeleteSync, "compare_size", return_value=is_size
        )
        mock_compare_time = mocker.patch.object(
            DeleteSync, "compare_time", return_value=is_time
        )
        assert (
            DeleteSync().determine_should_sync(FileStats(src=""), FileStats(src=""))
            is expected
        )
        mock_compare_size.assert_not_called()
        mock_compare_time.assert_not_called()

    def test_name(self) -> None:
        """Test name."""
        assert DeleteSync().name == "delete"
