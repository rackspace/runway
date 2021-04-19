"""Test runway.core.providers.aws.s3._helpers.filters."""
# pylint: disable=no-self-use
from __future__ import annotations

import pytest

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.filters import Filter, FilterPattern
from runway.core.providers.aws.s3._helpers.parameters import ParametersDataModel


class TestFilter:
    """Test Filter."""

    def test_call_local(self) -> None:
        """Test call."""
        exclude_md = FileStats(src="/src/exclude/README.md", src_type="local", dest="")
        include_md = FileStats(src="/src/include/README.md", src_type="local", dest="")
        other_file = FileStats(src="/src/test.txt", src_type="local", dest="")
        params = ParametersDataModel(
            src="/src",
            dest="s3://dest/",
            dir_op=True,
            exclude=["*/*.md"],
            include=["include/README.md"],
        )
        obj = Filter.parse_params(params)
        result = list(obj.call(iter([other_file, include_md, exclude_md])))
        assert exclude_md not in result
        assert include_md in result
        assert other_file in result
        assert len(result) == 2

    def test_call_s3(self) -> None:
        """Test call."""
        exclude_md = FileStats(src="/tmp/exclude/README.md", src_type="local", dest="")
        include_md = FileStats(src="bucket/include/README.md", src_type="s3", dest="")
        other_file = FileStats(src="bucket/test.txt", src_type="s3", dest="")
        params = ParametersDataModel(
            src="s3://bucket/",
            dest="/tmp",
            dir_op=True,
            exclude=["/tmp/exclude/README.md"],
        )
        obj = Filter.parse_params(params)
        result = list(obj.call(iter([other_file, include_md, exclude_md])))
        assert exclude_md not in result
        assert include_md in result
        assert other_file in result
        assert len(result) == 2

    def test_parse_params(self) -> None:
        """Test parse_params."""
        params = ParametersDataModel(
            src="/src",
            dest="s3://dest/",
            dir_op=True,
            exclude=["exclude/*"],
            include=["include/*"],
        )
        result = Filter.parse_params(params)
        assert isinstance(result, Filter)
        assert result.patterns == [
            FilterPattern("exclude", "/src/exclude/*"),
            FilterPattern("include", "/src/include/*"),
        ]
        assert result.dest_patterns == [
            FilterPattern("exclude", "dest/exclude/*"),
            FilterPattern("include", "dest/include/*"),
        ]

    def test_parse_params_no_filter(self) -> None:
        """Test parse_params."""
        params = ParametersDataModel(src="/src", dest="s3://dest/", dir_op=True)
        result = Filter.parse_params(params)
        assert result.patterns == []
        assert result.dest_patterns == []

    @pytest.mark.parametrize(
        "path, dir_op, expected",
        [
            ("s3://bucket", True, "bucket/"),
            ("s3://bucket/", False, "bucket/"),
            ("s3://bucket/prefix/key.txt", False, "bucket/prefix"),
            ("s3://bucket/prefix/", False, "bucket/prefix/"),
            ("/tmp/", True, "/tmp"),
            ("/tmp/", False, "/tmp"),
            ("/tmp", False, "/"),
            ("/tmp/dir/test.txt", False, "/tmp/dir"),
        ],
    )
    def test_parse_rootdir(self, dir_op: bool, expected: str, path: str) -> None:
        """Test parse_rootdir."""
        assert Filter.parse_rootdir(path, dir_op) == expected
