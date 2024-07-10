"""Test runway.core.providers.aws.s3._helpers.file_generator."""

from __future__ import annotations

import datetime
import os
import platform
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzlocal
from mock import Mock

from runway.core.providers.aws.s3._helpers.file_generator import (
    FileGenerator,
    FileStats,
    is_readable,
    is_special_file,
)
from runway.core.providers.aws.s3._helpers.format_path import FormatPath
from runway.core.providers.aws.s3._helpers.utils import EPOCH_TIME

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.file_generator import (
        FileStatsDict,
        _LastModifiedAndSize,
    )

    from .conftest import LocalFiles


MODULE = "runway.core.providers.aws.s3._helpers.file_generator"

NOW = datetime.datetime.now(tzlocal())


def test_is_readable(tmp_path: Path) -> None:
    """Test is_readable."""
    assert is_readable(tmp_path)
    tmp_file = tmp_path / "foo"
    tmp_file.write_text("foo")
    assert is_readable(tmp_file)


def test_is_readable_unreadable_directory(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test is_readable."""
    mocker.patch("os.listdir", side_effect=OSError)
    assert not is_readable(tmp_path)


def test_is_readable_unreadable_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test is_readable."""
    mocker.patch(f"{MODULE}.open", side_effect=OSError)
    tmp_file = tmp_path / "foo"
    tmp_file.write_text("foo")
    assert not is_readable(tmp_file)


def test_is_special_file(tmp_path: Path) -> None:
    """Test is_special_file."""
    tmp_file = tmp_path / "foo"
    tmp_file.touch()
    assert not is_special_file(tmp_file)


def test_is_special_file_block_device(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test is_special_file."""
    mocker.patch("stat.S_ISBLK", return_value=True)
    tmp_file = tmp_path / "foo"
    tmp_file.touch()
    assert is_special_file(tmp_file)


def test_is_special_file_character_device(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test is_special_file."""
    mocker.patch("stat.S_ISCHR", return_value=True)
    tmp_file = tmp_path / "foo"
    tmp_file.touch()
    assert is_special_file(tmp_file)


@pytest.mark.skipif(platform.system() == "Windows", reason="os.mknod requires Linux")
def test_is_special_file_fifo(tmp_path: Path) -> None:
    """Test is_special_file."""
    tmp_file = tmp_path / "foo"
    # method only exists on linux systems
    os.mknod(tmp_file, 0o600 | stat.S_IFIFO)  # type: ignore
    assert is_special_file(tmp_file)


def test_is_special_file_socket(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test is_special_file.

    Can't test with a real socket as tmp_path can be too long to bind to.

    """
    mocker.patch("stat.S_ISSOCK", return_value=True)
    tmp_file = tmp_path / "foo"
    tmp_file.touch()
    assert is_special_file(tmp_file)


class TestFileGenerator:
    """Test FileGenerator."""

    client: Mock

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.client = Mock()

    def test_call_locals3(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test call."""
        src = str(tmp_path) + os.sep
        dest = "s3://bucket/prefix/"
        formatted_path = FormatPath.format(src, dest)
        extra_info: _LastModifiedAndSize = {"LastModified": NOW, "Size": 13}
        mock_find_dest_path_comp_key = mocker.patch(
            f"{MODULE}.find_dest_path_comp_key",
            return_value=("dest-path", "compare-key"),
        )
        mock_list_files = mocker.patch.object(
            FileGenerator, "list_files", return_value=[(f"{src}test.txt", extra_info)]
        )
        mock_list_objects = mocker.patch.object(FileGenerator, "list_objects")
        assert list(FileGenerator(self.client, "operation").call(formatted_path)) == [
            FileStats(
                src=f"{src}test.txt",
                compare_key="compare-key",
                dest="dest-path",
                dest_type="s3",
                last_update=extra_info["LastModified"],
                operation_name="operation",
                response_data=None,
                size=extra_info["Size"],
                src_type="local",
            )
        ]
        mock_list_files.assert_called_once_with(
            formatted_path["src"]["path"], formatted_path["dir_op"]
        )
        mock_list_objects.assert_not_called()
        mock_find_dest_path_comp_key.assert_called_once_with(formatted_path, f"{src}test.txt")

    def test_call_s3local(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test call."""
        src = "s3://bucket/prefix/"
        dest = str(tmp_path) + os.sep
        formatted_path = FormatPath.format(src, dest)
        extra_info: _LastModifiedAndSize = {"LastModified": NOW, "Size": 13}
        mock_find_dest_path_comp_key = mocker.patch(
            f"{MODULE}.find_dest_path_comp_key",
            return_value=("dest-path", "compare-key"),
        )
        mock_list_files = mocker.patch.object(FileGenerator, "list_files")
        mock_list_objects = mocker.patch.object(
            FileGenerator, "list_objects", return_value=[(f"{src}test.txt", extra_info)]
        )
        assert list(FileGenerator(self.client, "operation").call(formatted_path)) == [
            FileStats(
                src=f"{src}test.txt",
                compare_key="compare-key",
                dest="dest-path",
                dest_type="local",
                last_update=extra_info["LastModified"],
                operation_name="operation",
                response_data=extra_info,  # type: ignore
                size=extra_info["Size"],
                src_type="s3",
            )
        ]
        mock_list_objects.assert_called_once_with(
            formatted_path["src"]["path"], formatted_path["dir_op"]
        )
        mock_list_files.assert_not_called()
        mock_find_dest_path_comp_key.assert_called_once_with(formatted_path, f"{src}test.txt")

    def test_list_files_directory(self, loc_files: LocalFiles, mocker: MockerFixture) -> None:
        """Test list_files."""
        mocker.patch(f"{MODULE}.get_file_stat", return_value=(15, NOW))
        mocker.patch.object(FileGenerator, "should_ignore_file", return_value=False)
        obj = FileGenerator(self.client, "")
        result = list(obj.list_files(str(loc_files["tmp_path"]), True))
        assert len(result) == 2
        assert (loc_files["files"][0], {"Size": 15, "LastModified": NOW}) in result
        assert (loc_files["files"][1], {"Size": 15, "LastModified": NOW}) in result

    def test_list_files_file(self, loc_files: LocalFiles, mocker: MockerFixture) -> None:
        """Test list_files."""
        mocker.patch(f"{MODULE}.get_file_stat", return_value=(15, NOW))
        mocker.patch.object(FileGenerator, "should_ignore_file", return_value=False)
        obj = FileGenerator(self.client, "")
        result = list(obj.list_files(str(loc_files["local_file"]), False))
        assert len(result) == 1
        assert result[0] == (loc_files["local_file"], {"Size": 15, "LastModified": NOW})

    def test_list_objects(self, mocker: MockerFixture) -> None:
        """Test list_objects."""
        mock_list_objects = Mock(
            return_value=[
                ("bucket/key.txt", {"Size": 13}),
                ("bucket/prefix/", {"Size": 0}),
            ]
        )
        mock_inst = Mock(list_objects=mock_list_objects)
        mock_class = mocker.patch(f"{MODULE}.BucketLister", return_value=mock_inst)
        params = {"key": "val"}
        obj = FileGenerator(self.client, "", request_parameters={"ListObjectsV2": params})
        result = list(obj.list_objects("bucket/", dir_op=True))
        mock_class.assert_called_once_with(self.client)
        mock_list_objects.assert_called_once_with(
            bucket="bucket", prefix="", page_size=None, extra_args=params
        )
        assert result == [mock_list_objects.return_value[0]]

    def test_list_objects_delete(self, mocker: MockerFixture) -> None:
        """Test list_objects."""
        mock_list_objects = Mock(
            return_value=[
                ("bucket/prefix/key.txt", {"Size": 13}),
                ("bucket/prefix/something/", {"Size": 0}),
            ]
        )
        mock_inst = Mock(list_objects=mock_list_objects)
        mock_class = mocker.patch(f"{MODULE}.BucketLister", return_value=mock_inst)
        params = {"key": "val"}
        obj = FileGenerator(self.client, "delete", request_parameters={"ListObjectsV2": params})
        result = list(obj.list_objects("bucket/prefix", dir_op=True))
        mock_class.assert_called_once_with(self.client)
        mock_list_objects.assert_called_once_with(
            bucket="bucket", prefix="prefix", page_size=None, extra_args=params
        )
        assert result == mock_list_objects.return_value

    def test_list_objects_incorrect_dir_opt(self, mocker: MockerFixture) -> None:
        """Test list_objects."""
        mock_list_objects = Mock(
            return_value=[
                ("bucket/prefix/key.txt", {"Size": 13}),
                ("bucket/prefix/", {"Size": 0}),
            ]
        )
        mock_inst = Mock(list_objects=mock_list_objects)
        mock_class = mocker.patch(f"{MODULE}.BucketLister", return_value=mock_inst)
        obj = FileGenerator(self.client, "")
        result = list(obj.list_objects("bucket/", dir_op=False))
        mock_class.assert_called_once_with(self.client)
        mock_list_objects.assert_called_once_with(
            bucket="bucket", prefix="", page_size=None, extra_args={}
        )
        assert not result

    def test_list_objects_single(self) -> None:
        """Test list_objects."""
        head_object = Mock(return_value={"ContentLength": "13", "LastModified": NOW.isoformat()})
        self.client.head_object = head_object
        obj = FileGenerator(self.client, "")
        result = list(obj.list_objects("bucket/key.txt", False))
        assert len(result) == 1
        assert result[0] == ("bucket/key.txt", {"LastModified": NOW, "Size": 13})
        head_object.assert_called_once_with(Bucket="bucket", Key="key.txt")

    def test_list_objects_single_client_error_403(self) -> None:
        """Test list_objects."""
        exc = ClientError({"Error": {"Code": "403", "Message": ""}}, "HeadObject")
        head_object = Mock(side_effect=exc)
        self.client.head_object = head_object
        with pytest.raises(ClientError) as excinfo:
            list(FileGenerator(self.client, "").list_objects("bucket/key.txt", False))
        assert excinfo.value == exc

    def test_list_objects_single_client_error_404(self) -> None:
        """Test list_objects."""
        exc = ClientError({"Error": {"Code": "404", "Message": "something"}}, "HeadObject")
        head_object = Mock(side_effect=exc)
        self.client.head_object = head_object
        with pytest.raises(ClientError) as excinfo:
            list(FileGenerator(self.client, "").list_objects("bucket/key.txt", False))
        assert excinfo.value != exc
        assert excinfo.value.response["Error"]["Message"] == 'Key "key.txt" does not exist'

    def test_list_objects_single_delete(self) -> None:
        """Test list_objects."""
        obj = FileGenerator(self.client, "delete")
        result = list(obj.list_objects("bucket/key.txt", False))
        assert len(result) == 1
        assert result[0] == ("bucket/key.txt", {"Size": None, "LastModified": None})

    def test_normalize_sort(self) -> None:
        """Test normalize_sort."""
        names = [
            "xyz123456789",
            "xyz1" + os.path.sep + "test",
            "xyz" + os.path.sep + "test",
        ]
        ref_names = [names[2], names[1], names[0]]
        FileGenerator.normalize_sort(names, os.path.sep, "/")
        assert names == ref_names

    def test_normalize_sort_backslash(self) -> None:
        """Test normalize_sort."""
        names = ["xyz123456789", "xyz1\\test", "xyz\\test"]
        ref_names = [names[2], names[1], names[0]]
        FileGenerator.normalize_sort(names, "\\", "/")
        assert names == ref_names

    def test_safely_get_file_stats(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test safely_get_file_stats."""
        mock_get_file_stat = mocker.patch(f"{MODULE}.get_file_stat", return_value=(15, NOW))
        obj = FileGenerator(self.client, "")
        assert obj.safely_get_file_stats(tmp_path) == (
            tmp_path,
            {"Size": 15, "LastModified": NOW},
        )
        mock_get_file_stat.assert_called_once_with(tmp_path)

    def test_safely_get_file_stats_handle_os_error(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test safely_get_file_stats."""
        mocker.patch(f"{MODULE}.get_file_stat", side_effect=OSError)
        mock_triggers_warning = mocker.patch.object(FileGenerator, "triggers_warning")
        obj = FileGenerator(self.client, "")
        assert not obj.safely_get_file_stats(tmp_path)
        mock_triggers_warning.assert_called_once_with(tmp_path)

    def test_safely_get_file_stats_no_last_update(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test safely_get_file_stats."""
        mock_create_warning = mocker.patch(f"{MODULE}.create_warning", return_value="warning")
        mocker.patch(f"{MODULE}.get_file_stat", return_value=(15, None))
        obj = FileGenerator(self.client, "")
        assert obj.safely_get_file_stats(tmp_path) == (
            tmp_path,
            {"Size": 15, "LastModified": EPOCH_TIME},
        )
        mock_create_warning.assert_called_once_with(
            path=tmp_path,
            error_message="File has an invalid timestamp. Passing epoch " "time as timestamp.",
            skip_file=False,
        )
        assert obj.result_queue.get() == "warning"

    def test_should_ignore_file(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test should_ignore_file."""
        mock_triggers_warning = mocker.patch.object(
            FileGenerator, "triggers_warning", return_value=False
        )
        assert not FileGenerator(self.client, "", follow_symlinks=True).should_ignore_file(tmp_path)
        mock_triggers_warning.assert_called_once_with(tmp_path)

    def test_should_ignore_file_symlink(self, tmp_path: Path) -> None:
        """Test should_ignore_file."""
        tmp_symlink = tmp_path / "symlink"
        real_path = tmp_path / "real_path"
        real_path.mkdir()
        tmp_symlink.symlink_to(real_path)
        assert FileGenerator(self.client, "", follow_symlinks=False).should_ignore_file(tmp_symlink)

    def test_should_ignore_file_triggers_warning(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test should_ignore_file."""
        mocker.patch.object(FileGenerator, "triggers_warning", return_value=True)
        assert FileGenerator(self.client, "", follow_symlinks=True).should_ignore_file(tmp_path)

    def test_triggers_warning(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test triggers_warning."""
        mock_create_warning = mocker.patch(f"{MODULE}.create_warning")
        mock_is_special_file = mocker.patch(f"{MODULE}.is_special_file", return_value=False)
        mock_is_readable = mocker.patch(f"{MODULE}.is_readable", return_value=True)
        assert not FileGenerator(self.client, "", follow_symlinks=True).triggers_warning(tmp_path)
        mock_is_special_file.assert_called_once_with(tmp_path)
        mock_is_readable.assert_called_once_with(tmp_path)
        mock_create_warning.assert_not_called()

    def test_triggers_warning_does_not_exist(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test triggers_warning."""
        missing_path = tmp_path / "missing"
        mock_create_warning = mocker.patch(f"{MODULE}.create_warning", return_value="warning")
        mock_is_special_file = mocker.patch(f"{MODULE}.is_special_file", return_value=False)
        mock_is_readable = mocker.patch(f"{MODULE}.is_readable", return_value=True)
        obj = FileGenerator(self.client, "", follow_symlinks=True)
        assert obj.triggers_warning(missing_path)
        mock_is_special_file.assert_not_called()
        mock_is_readable.assert_not_called()
        mock_create_warning.assert_called_once_with(missing_path, "File does not exist.")
        assert obj.result_queue.get() == "warning"

    def test_triggers_warning_is_special_file(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test triggers_warning."""
        mock_create_warning = mocker.patch(f"{MODULE}.create_warning", return_value="warning")
        mock_is_special_file = mocker.patch(f"{MODULE}.is_special_file", return_value=True)
        mock_is_readable = mocker.patch(f"{MODULE}.is_readable", return_value=True)
        obj = FileGenerator(self.client, "", follow_symlinks=True)
        assert obj.triggers_warning(tmp_path)
        mock_is_special_file.assert_called_once_with(tmp_path)
        mock_is_readable.assert_not_called()
        mock_create_warning.assert_called_once_with(
            tmp_path,
            "File is character special device, block special device, FIFO, or socket.",
        )
        assert obj.result_queue.get() == "warning"

    def test_triggers_warning_is_unreadable(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test triggers_warning."""
        mock_create_warning = mocker.patch(f"{MODULE}.create_warning", return_value="warning")
        mock_is_special_file = mocker.patch(f"{MODULE}.is_special_file", return_value=False)
        mock_is_readable = mocker.patch(f"{MODULE}.is_readable", return_value=False)
        obj = FileGenerator(self.client, "", follow_symlinks=True)
        assert obj.triggers_warning(tmp_path)
        mock_is_special_file.assert_called_once_with(tmp_path)
        mock_is_readable.assert_called_once_with(tmp_path)
        mock_create_warning.assert_called_once_with(tmp_path, "File/Directory is not readable.")
        assert obj.result_queue.get() == "warning"


class TestFileStats:
    """Test FileStats."""

    def test_dict(self) -> None:
        """Test dict."""
        data: FileStatsDict = {
            "src": "/path/test.txt",
            "compare_key": "compare-key",
            "dest": "s3://dest-path",
            "dest_type": "s3",
            "last_update": NOW,
            "operation_name": "test",
            "response_data": None,  # type: ignore
            "size": 13,
            "src_type": "local",
        }
        assert FileStats(**data).dict() == data
