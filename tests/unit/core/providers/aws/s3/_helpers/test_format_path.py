"""Test runway.core.providers.aws.s3._helpers.format_path."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Tuple

import pytest
from mock import call

from runway.core.providers.aws.s3._helpers.format_path import FormatPath

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.format_path import SupportedPathType


class TestFormatPath:
    """Test FormatPath."""

    def test_format(self, mocker: MockerFixture) -> None:
        """Test format."""
        src = "/tmp/test/"
        dest = "s3://bucket/"
        mock_identify_path_type = mocker.patch.object(
            FormatPath,
            "identify_path_type",
            side_effect=[("local", src), ("s3", dest[:5])],
        )
        mock_format_local_path = mocker.patch.object(
            FormatPath, "format_local_path", return_value=(src, True)
        )
        mock_format_s3_path = mocker.patch.object(
            FormatPath, "format_s3_path", return_value=(dest[:5], True)
        )
        assert FormatPath.format(src, dest) == {
            "dest": {"path": dest[:5], "type": "s3"},
            "dir_op": True,
            "src": {"path": src, "type": "local"},
            "use_src_name": True,
        }
        mock_identify_path_type.assert_has_calls([call(src), call(dest)])  # type: ignore
        mock_format_local_path.assert_called_once_with(src)
        mock_format_s3_path.assert_called_once_with(dest[:5])

    def test_format_local_path(self, tmp_path: Path) -> None:
        """Test format_local_path."""
        missing_path = tmp_path / "missing"
        str_missing_path = str(missing_path)
        str_tmp_path = str(tmp_path)
        assert FormatPath.format_local_path(str_tmp_path, False) == (
            str_tmp_path + os.sep,
            True,
        )
        assert FormatPath.format_local_path(str_tmp_path, True) == (
            str_tmp_path + os.sep,
            True,
        )
        assert FormatPath.format_local_path(str_missing_path, True) == (
            str_missing_path + os.sep,
            True,
        )
        assert FormatPath.format_local_path(str_missing_path, False) == (
            str_missing_path,
            False,
        )
        assert FormatPath.format_local_path(str_missing_path + os.sep, False) == (
            str_missing_path + os.sep,
            True,
        )

    @pytest.mark.parametrize(
        "path, dir_op, expected",
        [
            ("s3://bucket", True, ("s3://bucket/", True)),
            ("s3://bucket/", True, ("s3://bucket/", True)),
            ("s3://bucket/", False, ("s3://bucket/", True)),
            ("s3://bucket", False, ("s3://bucket", False)),
            ("s3://bucket/key.txt", False, ("s3://bucket/key.txt", False)),
        ],
    )
    def test_format_s3_path(self, dir_op: bool, expected: Tuple[str, bool], path: str) -> None:
        """Test format_s3_path."""
        assert FormatPath.format_s3_path(path, dir_op) == expected

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("/test/file.txt", ("local", "/test/file.txt")),
            ("test/file.txt", ("local", "test/file.txt")),
            ("/test/", ("local", "/test/")),
            ("s3://test/file.txt", ("s3", "test/file.txt")),
            ("s3://test/", ("s3", "test/")),
            ("s3://test", ("s3", "test")),
        ],
    )
    def test_identify_path_type(self, expected: Tuple[SupportedPathType, str], path: str) -> None:
        """Test identify_path_type."""
        assert FormatPath.identify_path_type(path) == expected
