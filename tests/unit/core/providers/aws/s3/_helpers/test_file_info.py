"""Test runway.core.providers.aws.s3._helpers.file_info."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytest
from typing_extensions import Literal

from runway.core.providers.aws.s3._helpers.file_info import FileInfo
from runway.core.providers.aws.s3._helpers.utils import EPOCH_TIME

if TYPE_CHECKING:
    from pathlib import Path

    from mypy_boto3_s3.type_defs import ObjectTypeDef


NOW = datetime.datetime.now()


def build_object_data(
    *,
    storage_class: Literal[
        "DEEP_ARCHIVE",
        "GLACIER",
        "INTELLIGENT_TIERING",
        "ONEZONE_IA",
        "OUTPOSTS",
        "REDUCED_REDUNDANCY",
        "STANDARD",
        "STANDARD_IA",
    ] = "STANDARD",
) -> ObjectTypeDef:
    """Build object data."""
    return {
        "Key": "test.txt",
        "LastModified": NOW,
        "ETag": "",
        "Size": 10,
        "StorageClass": storage_class,
    }


class TestFileInfo:
    """Test FileInfo."""

    def test_init_default(self, tmp_path: Path) -> None:
        """Test __init__."""
        obj = FileInfo(tmp_path)
        assert obj.src == tmp_path
        assert not obj.src_type
        assert not obj.operation_name
        assert not obj.client
        assert not obj.dest
        assert not obj.dest_type
        assert not obj.compare_key
        assert not obj.size
        assert obj.last_update == EPOCH_TIME
        assert obj.parameters == {}
        assert not obj.source_client
        assert not obj.is_stream
        assert not obj.associated_response_data

    @pytest.mark.parametrize(
        "storage_class, expected",
        [
            ("DEEP_ARCHIVE", False),
            ("GLACIER", False),
            ("INTELLIGENT_TIERING", True),
            ("ONEZONE_IA", True),
            ("OUTPOSTS", True),
            ("REDUCED_REDUNDANCY", True),
            ("STANDARD", True),
            ("STANDARD_IA", True),
        ],
    )
    def test_is_glacier_compatible_copy_download(
        self,
        expected: bool,
        storage_class: Literal[
            "DEEP_ARCHIVE",
            "GLACIER",
            "INTELLIGENT_TIERING",
            "ONEZONE_IA",
            "OUTPOSTS",
            "REDUCED_REDUNDANCY",
            "STANDARD",
            "STANDARD_IA",
        ],
    ) -> None:
        """Test is_glacier_compatible."""
        assert (
            FileInfo(
                "",
                response_data=build_object_data(storage_class=storage_class),
                operation_name="copy",
            ).is_glacier_compatible
            is expected
        )
        assert (
            FileInfo(
                "",
                response_data=build_object_data(storage_class=storage_class),
                operation_name="download",
            ).is_glacier_compatible
            is expected
        )

    @pytest.mark.parametrize(
        "storage_class, expected",
        [
            ("DEEP_ARCHIVE", False),
            ("GLACIER", False),
            ("INTELLIGENT_TIERING", True),
            ("ONEZONE_IA", True),
            ("OUTPOSTS", True),
            ("REDUCED_REDUNDANCY", True),
            ("STANDARD", True),
            ("STANDARD_IA", True),
        ],
    )
    def test_is_glacier_compatible_move(
        self,
        expected: bool,
        storage_class: Literal[
            "DEEP_ARCHIVE",
            "GLACIER",
            "INTELLIGENT_TIERING",
            "ONEZONE_IA",
            "OUTPOSTS",
            "REDUCED_REDUNDANCY",
            "STANDARD",
            "STANDARD_IA",
        ],
    ) -> None:
        """Test is_glacier_compatible."""
        assert (
            FileInfo(
                "",
                src_type="s3",
                response_data=build_object_data(storage_class=storage_class),
                operation_name="move",
            ).is_glacier_compatible
            is expected
        )
        assert (
            FileInfo(
                "",
                src_type="local",
                response_data=build_object_data(storage_class=storage_class),
            ).is_glacier_compatible
            is True
        )

    def test_is_glacier_compatible_no_response_data(self) -> None:
        """Test is_glacier_compatible."""
        assert FileInfo("").is_glacier_compatible

    @pytest.mark.parametrize("storage_class", ["DEEP_ARCHIVE", "GLACIER"])
    def test_is_glacier_compatible_restored(
        self,
        storage_class: Literal[
            "DEEP_ARCHIVE",
            "GLACIER",
            "INTELLIGENT_TIERING",
            "ONEZONE_IA",
            "OUTPOSTS",
            "REDUCED_REDUNDANCY",
            "STANDARD",
            "STANDARD_IA",
        ],
    ) -> None:
        """Test is_glacier_compatible."""
        assert (
            FileInfo(
                "",
                operation_name="copy",
                response_data={  # type: ignore
                    "Restore": 'ongoing-request="false"',
                    **build_object_data(storage_class=storage_class),
                },
            ).is_glacier_compatible
            is True
        )
