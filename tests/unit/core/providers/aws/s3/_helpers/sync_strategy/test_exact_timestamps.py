"""Test runway.core.providers.aws.s3._helpers.sync_strategy.exact_timestamps."""

from __future__ import annotations

import datetime
from typing import Optional

import pytest
from mock import Mock

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.sync_strategy.exact_timestamps import (
    ExactTimestampsSync,
)

MODULE = "runway.core.providers.aws.s3._helpers.sync_strategy.exact_timestamps"


class TestExactTimestampsSync:
    """Test ExactTimestampsSync."""

    def test_compare_time_dest_older(self) -> None:
        """Test compare_time."""
        time_src = datetime.datetime.now()
        time_dest = time_src - datetime.timedelta(days=1)
        assert (
            ExactTimestampsSync().compare_time(
                FileStats(src="", last_update=time_src, operation_name="download"),
                FileStats(src="", last_update=time_dest),
            )
            is False
        )

    def test_compare_time_dest_older_not_download(self) -> None:
        """Test compare_time."""
        time_src = datetime.datetime.now()
        time_dest = time_src - datetime.timedelta(days=1)
        assert (
            ExactTimestampsSync().compare_time(
                FileStats(src="", last_update=time_src, operation_name="invalid"),
                FileStats(src="", last_update=time_dest),
            )
            is False
        )

    @pytest.mark.parametrize(
        "src, dest", [(None, None), (Mock(), None), (None, Mock())]
    )
    def test_compare_time_raise_value_error(
        self, dest: Optional[FileStats], src: Optional[FileStats]
    ) -> None:
        """Test compare_time."""
        with pytest.raises(ValueError) as excinfo:
            ExactTimestampsSync().compare_time(src, dest)
        assert str(excinfo.value) == "src_file and dest_file must not be None"

    def test_compare_time_same(self) -> None:
        """Test compare_time."""
        now = datetime.datetime.now()
        assert (
            ExactTimestampsSync().compare_time(
                FileStats(src="", last_update=now, operation_name="download"),
                FileStats(src="", last_update=now),
            )
            is True
        )

    def test_compare_time_src_older(self) -> None:
        """Test compare_time."""
        time_dest = datetime.datetime.now()
        time_src = time_dest - datetime.timedelta(days=1)
        assert (
            ExactTimestampsSync().compare_time(
                FileStats(src="", last_update=time_src, operation_name="download"),
                FileStats(src="", last_update=time_dest),
            )
            is False
        )

    def test_name(self) -> None:
        """Test name."""
        assert ExactTimestampsSync().name == "exact_timestamps"
