"""Test runway.core.providers.aws.s3._helpers.filters."""

from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.filters import Filter, FilterPattern
from runway.core.providers.aws.s3._helpers.parameters import ParametersDataModel

CWD = Path.cwd()


class TestFilter:
    """Test Filter."""

    def test_call_local(self, tmp_path: Path) -> None:
        """Test call."""
        exclude_md = FileStats(
            src=tmp_path / "exclude/README.md", src_type="local", dest=""
        )
        include_md = FileStats(
            src=tmp_path / "include/README.md", src_type="local", dest=""
        )
        other_file = FileStats(src=tmp_path / "/test.txt", src_type="local", dest="")
        params = ParametersDataModel(
            src=str(tmp_path),
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

    def test_parse_params(self, tmp_path: Path) -> None:
        """Test parse_params."""
        params = ParametersDataModel(
            src=str(tmp_path),
            dest="s3://dest/",
            dir_op=True,
            exclude=["exclude/*"],
            include=["include/*"],
        )
        result = Filter.parse_params(params)
        assert isinstance(result, Filter)
        assert result.patterns == [
            FilterPattern("exclude", f"{tmp_path}{os.sep}exclude/*"),
            FilterPattern("include", f"{tmp_path}{os.sep}include/*"),
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
    @pytest.mark.skipif(platform.system() == "Windows", reason="POSIX paths")
    def test_parse_rootdir(self, dir_op: bool, expected: str, path: str) -> None:
        """Test parse_rootdir."""
        assert Filter.parse_rootdir(path, dir_op) == expected

    @pytest.mark.parametrize(
        "path, dir_op, expected",
        [
            ("s3://bucket", True, "bucket/"),
            ("s3://bucket/", False, "bucket/"),
            ("s3://bucket/prefix/key.txt", False, "bucket/prefix"),
            ("s3://bucket/prefix/", False, "bucket/prefix/"),
            ("/tmp", True, f"{CWD.drive}\\tmp"),
            ("/tmp/", False, f"{CWD.drive}\\tmp"),
            ("/tmp", False, f"{CWD.drive}\\"),
            ("/tmp/dir/test.txt", False, f"{CWD.drive}\\tmp\\dir"),
        ],
    )
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows paths")
    def test_parse_rootdir_win(self, dir_op: bool, expected: str, path: str) -> None:
        """Test parse_rootdir for Windows."""
        assert Filter.parse_rootdir(path, dir_op) == expected
