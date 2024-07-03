"""Test runway.core.providers.aws.s3._helpers.utils."""

# pylint: disable=too-many-lines
from __future__ import annotations

import datetime
import errno
import ntpath
import os
import platform
import posixpath
import time
from io import BytesIO
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.hooks import HierarchicalEmitter
from botocore.stub import Stubber
from dateutil.tz import tzlocal
from mock import Mock, PropertyMock, sentinel
from s3transfer.compat import seekable
from s3transfer.futures import TransferFuture

from runway.core.providers.aws.s3._helpers.format_path import (
    FormatPathResult,
    FormattedPathDetails,
)
from runway.core.providers.aws.s3._helpers.utils import (
    BaseProvideContentTypeSubscriber,
    BucketLister,
    CreateDirectoryError,
    DeleteCopySourceObjectSubscriber,
    DeleteSourceFileSubscriber,
    DeleteSourceObjectSubscriber,
    DeleteSourceSubscriber,
    DirectoryCreatorSubscriber,
    NonSeekableStream,
    OnDoneFilteredSubscriber,
    PrintTask,
    ProvideCopyContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber,
    ProvideSizeSubscriber,
    ProvideUploadContentTypeSubscriber,
    RequestParamsMapper,
    SetFileUtimeError,
    StdoutBytesWriter,
    _date_parser,
    block_s3_object_lambda,
    create_warning,
    find_bucket_key,
    find_dest_path_comp_key,
    get_file_stat,
    guess_content_type,
    human_readable_size,
    human_readable_to_bytes,
    relative_path,
    set_file_utime,
    uni_print,
)

from .factories import (
    FakeTransferFuture,
    FakeTransferFutureCallArgs,
    FakeTransferFutureMeta,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.aws.s3._helpers.utils"


class TestBaseProvideContentTypeSubscriber:
    """Test BaseProvideContentTypeSubscriber."""

    def test_on_queued(self) -> None:
        """Test on_queued."""
        with pytest.raises(NotImplementedError) as excinfo:
            BaseProvideContentTypeSubscriber().on_queued(Mock())
        assert str(excinfo.value) == "_get_filename()"


class TestBucketLister:
    """Test BucketLister."""

    date_parser: ClassVar[Mock] = Mock(return_value=sentinel.now)
    emitter: ClassVar[HierarchicalEmitter] = HierarchicalEmitter()
    client: ClassVar[Mock] = Mock(meta=Mock(events=emitter))
    responses: List[Any] = []

    def fake_paginate(self, *_args: Any, **_kwargs: Any) -> List[Any]:
        """Fake paginate."""
        for response in self.responses:
            self.emitter.emit("after-call.s3.ListObjectsV2", parsed=response)
        return self.responses

    def test_list_objects(self) -> None:
        """Test list_objects."""
        now = sentinel.now
        self.client.get_paginator.return_value.paginate = self.fake_paginate
        individual_response_elements = [
            {"LastModified": "2014-02-27T04:20:38.000Z", "Key": "a", "Size": 1},
            {"LastModified": "2014-02-27T04:20:38.000Z", "Key": "b", "Size": 2},
            {"LastModified": "2014-02-27T04:20:38.000Z", "Key": "c", "Size": 3},
        ]
        self.responses = [
            {"Contents": individual_response_elements[0:2]},
            {"Contents": [individual_response_elements[2]]},
        ]
        lister = BucketLister(self.client, self.date_parser)
        result = list(lister.list_objects(bucket="foo"))
        assert result == [
            ("foo/a", individual_response_elements[0]),
            ("foo/b", individual_response_elements[1]),
            ("foo/c", individual_response_elements[2]),
        ]
        for individual_response in individual_response_elements:
            assert individual_response["LastModified"] == now

    def test_list_objects_pass_extra_args(self):
        """Test list_objects."""
        self.client.get_paginator.return_value.paginate = Mock(
            return_value=[
                {
                    "Contents": [
                        {
                            "LastModified": "2014-02-27T04:20:38.000Z",
                            "Key": "key",
                            "Size": 3,
                        }
                    ]
                }
            ]
        )
        lister = BucketLister(self.client, self.date_parser)
        list(
            lister.list_objects(
                bucket="mybucket", extra_args={"RequestPayer": "requester"}
            )
        )
        self.client.get_paginator.return_value.paginate.assert_called_with(
            Bucket="mybucket",
            PaginationConfig={"PageSize": None},
            RequestPayer="requester",
        )

    def test_list_objects_pass_prefix(self):
        """Test list_objects."""
        self.client.get_paginator.return_value.paginate = Mock(
            return_value=[
                {
                    "Contents": [
                        {
                            "LastModified": "2014-02-27T04:20:38.000Z",
                            "Key": "key",
                            "Size": 3,
                        }
                    ]
                }
            ]
        )
        lister = BucketLister(self.client, self.date_parser)
        list(lister.list_objects(bucket="mybucket", prefix="prefix"))
        self.client.get_paginator.return_value.paginate.assert_called_with(
            Bucket="mybucket", PaginationConfig={"PageSize": None}, Prefix="prefix"
        )


class TestDeleteCopySourceObjectSubscriber:
    """Test DeleteCopySourceObjectSubscriber."""

    bucket: ClassVar[str] = "test-bucket"
    key: ClassVar[str] = "test.txt"
    meta: ClassVar[FakeTransferFutureMeta] = FakeTransferFutureMeta(
        call_args=FakeTransferFutureCallArgs(copy_source={"Bucket": bucket, "Key": key})
    )

    def test_on_done_delete(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_response(
            "delete_object", {}, {"Bucket": self.bucket, "Key": self.key}
        )
        future = Mock(meta=self.meta)
        with stubber:
            assert not DeleteCopySourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_not_called()

    def test_on_done_delete_request_payer(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_response(
            "delete_object",
            {},
            {"Bucket": self.bucket, "Key": self.key, "RequestPayer": "requester"},
        )
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(
                    copy_source={"Bucket": self.bucket, "Key": self.key},
                    extra_args={"RequestPayer": "requester"},
                )
            )
        )
        with stubber:
            assert not DeleteCopySourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_not_called()

    def test_on_done_exception(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_client_error("delete_object")
        future = Mock(meta=self.meta)
        with stubber:
            assert not DeleteCopySourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_called_once()
        assert isinstance(future.set_exception.call_args[0][0], ClientError)


class TestDeleteSourceFileSubscriber:
    """Test DeleteSourceFileSubscriber."""

    def test_on_done_delete(self, tmp_path: Path) -> None:
        """Test on_done."""
        tmp_file = tmp_path / "test.txt"
        tmp_file.write_text("data")
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=str(tmp_file))
            )
        )
        DeleteSourceFileSubscriber().on_done(future)
        assert not tmp_file.exists()
        future.set_exception.assert_not_called()

    def test_on_done_exception(self, tmp_path: Path) -> None:
        """Test on_done."""
        tmp_file = tmp_path / "test.txt"
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=str(tmp_file))
            )
        )
        DeleteSourceFileSubscriber().on_done(future)
        assert not tmp_file.exists()
        future.set_exception.assert_called_once()
        assert isinstance(future.set_exception.call_args[0][0], EnvironmentError)


class TestDeleteSourceObjectSubscriber:
    """Test DeleteSourceObjectSubscriber."""

    bucket: ClassVar[str] = "test-bucket"
    key: ClassVar[str] = "test.txt"
    meta: ClassVar[FakeTransferFutureMeta] = FakeTransferFutureMeta(
        call_args=FakeTransferFutureCallArgs(bucket=bucket, key=key)
    )

    def test_on_done_delete(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_response(
            "delete_object", {}, {"Bucket": self.bucket, "Key": self.key}
        )
        future = Mock(meta=self.meta)
        with stubber:
            assert not DeleteSourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_not_called()

    def test_on_done_delete_request_payer(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_response(
            "delete_object",
            {},
            {"Bucket": self.bucket, "Key": self.key, "RequestPayer": "requester"},
        )
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(
                    bucket=self.bucket,
                    key=self.key,
                    extra_args={"RequestPayer": "requester"},
                )
            )
        )
        with stubber:
            assert not DeleteSourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_not_called()

    def test_on_done_exception(self) -> None:
        """Test on_done."""
        client = boto3.client("s3")
        stubber = Stubber(client)
        stubber.add_client_error("delete_object")
        future = Mock(meta=self.meta)
        with stubber:
            assert not DeleteSourceObjectSubscriber(client).on_done(future)
        future.set_exception.assert_called_once()
        assert isinstance(future.set_exception.call_args[0][0], ClientError)


class TestDeleteSourceSubscriber:
    """Test DeleteSourceSubscriber."""

    def test_on_done(self) -> None:
        """Test on_done."""
        future = Mock()
        assert not DeleteSourceSubscriber().on_done(future)
        assert isinstance(future.set_exception.call_args[0][0], NotImplementedError)
        assert str(future.set_exception.call_args[0][0]) == "_delete_source()"  # type: ignore


class TestDirectoryCreatorSubscriber:
    """Test DirectoryCreatorSubscriber."""

    def test_on_queued(self, tmp_path: Path) -> None:
        """Test on_queued."""
        tmp_dir = tmp_path / "test_dir"
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_dir / "test.txt")
            )
        )
        assert not DirectoryCreatorSubscriber().on_queued(future)  # type: ignore
        assert tmp_dir.is_dir()
        future.set_exception.assert_not_called()

    def test_on_queued_exists(self, tmp_path: Path) -> None:
        """Test on_queued."""
        tmp_dir = tmp_path / "test_dir"
        tmp_dir.mkdir()
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_dir / "test.txt")
            )
        )
        assert not DirectoryCreatorSubscriber().on_queued(future)  # type: ignore
        assert tmp_dir.is_dir()
        future.set_exception.assert_not_called()

    def test_on_queued_handle_eexist(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test on_queued."""
        tmp_dir = tmp_path / "test_dir"
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_dir / "test.txt")
            )
        )
        exc = OSError()
        exc.errno = errno.EEXIST
        mocker.patch("os.makedirs", side_effect=exc)
        assert not DirectoryCreatorSubscriber().on_queued(future)
        assert not tmp_dir.exists()

    def test_on_queued_os_error(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test on_queued."""
        tmp_dir = tmp_path / "test_dir"
        future = Mock(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_dir / "test.txt")
            )
        )
        mocker.patch("os.makedirs", side_effect=OSError())
        with pytest.raises(CreateDirectoryError):
            DirectoryCreatorSubscriber().on_queued(future)
        assert not tmp_dir.exists()


class TestNonSeekableStream:
    """Test NonSeekableStream."""

    def test_can_make_stream_unseekable(self) -> None:
        """Test can make stream unseekable."""
        fileobj = BytesIO(b"foobar")
        assert seekable(fileobj)
        nonseekable_fileobj = NonSeekableStream(fileobj)
        assert not seekable(nonseekable_fileobj)
        assert nonseekable_fileobj.read() == b"foobar"

    def test_can_specify_amount_for_nonseekable_stream(self) -> None:
        """Test can specify amount for nonseekable stream."""
        assert NonSeekableStream(BytesIO(b"foobar")).read(3) == b"foo"


class TestOnDoneFilteredSubscriber:
    """Test OnDoneFilteredSubscriber."""

    class Subscriber(OnDoneFilteredSubscriber):
        """Subscriber subclass to test."""

        def __init__(self):
            """Instantiate class."""
            self.on_success_calls: List[Any] = []
            self.on_failure_calls: List[Any] = []

        def _on_success(self, future: Any) -> None:
            self.on_success_calls.append(future)

        def _on_failure(self, future: Any, exception: Exception) -> None:
            self.on_failure_calls.append((future, exception))

    def test_on_done_failure(self):
        """Test on_done."""
        subscriber = self.Subscriber()
        exception = Exception("my exception")
        future = FakeTransferFuture(exception=exception)
        subscriber.on_done(future)  # type: ignore
        assert subscriber.on_failure_calls == [(future, exception)]
        assert not subscriber.on_success_calls and isinstance(
            subscriber.on_success_calls, list
        )

    def test_on_done_success(self):
        """Test on_done."""
        subscriber = self.Subscriber()
        future = FakeTransferFuture("return-value")
        subscriber.on_done(future)  # type: ignore
        assert subscriber.on_success_calls == [future]
        assert not subscriber.on_failure_calls and isinstance(
            subscriber.on_failure_calls, list
        )


class TestProvideCopyContentTypeSubscriber:
    """Test ProvideCopyContentTypeSubscriber."""

    key: ClassVar[str] = "test.txt"

    def test_on_queued(self, mocker: MockerFixture) -> None:
        """Test on_queued."""
        future = FakeTransferFuture(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(copy_source={"Key": self.key})
            )
        )
        mock_guess_content_type = mocker.patch(
            f"{MODULE}.guess_content_type", return_value="something"
        )
        assert not ProvideCopyContentTypeSubscriber().on_queued(future)  # type: ignore
        mock_guess_content_type.assert_called_once_with(self.key)
        assert future.meta.call_args.extra_args.get("ContentType") == "something"


class TestProvideLastModifiedTimeSubscriber:
    """Test ProvideLastModifiedTimeSubscriber."""

    desired_utime: ClassVar[datetime.datetime] = datetime.datetime(
        2016, 1, 18, 7, 0, 0, tzinfo=tzlocal()
    )
    result_queue: ClassVar["Queue[Any]"] = Queue()
    subscriber: ClassVar[ProvideLastModifiedTimeSubscriber] = (
        ProvideLastModifiedTimeSubscriber(desired_utime, result_queue)
    )

    def test_on_done_handle_exception(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test on_done."""
        tmp_file = tmp_path / "test.txt"
        tmp_file.touch()
        future = FakeTransferFuture(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_file)
            )
        )
        mock_create_warning = mocker.patch(
            f"{MODULE}.create_warning", return_value="warning"
        )
        assert not ProvideLastModifiedTimeSubscriber(
            None, self.result_queue  # type: ignore
        ).on_done(
            future  # type: ignore
        )
        mock_create_warning.assert_called_once()
        assert mock_create_warning.call_args[0][0] == tmp_file
        assert (
            "was unable to update the last modified time."
            in mock_create_warning.call_args[0][1]
        )
        assert self.result_queue.get() == "warning"

    def test_on_done_modifies_utime(self, tmp_path: Path) -> None:
        """Test on_done."""
        tmp_file = tmp_path / "test.txt"
        tmp_file.touch()
        future = FakeTransferFuture(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj=tmp_file)
            )
        )
        assert not self.subscriber.on_done(future)  # type: ignore
        _, utime = get_file_stat(tmp_file)
        assert utime == self.desired_utime


class TestProvideSizeSubscriber:
    """Test ProvideSizeSubscriber."""

    def test_on_queued_set_size(self) -> None:
        """Test on_queued."""
        future = Mock(spec=TransferFuture)
        meta = Mock()
        future.meta = meta
        assert not ProvideSizeSubscriber(10).on_queued(future)
        meta.provide_transfer_size.assert_called_once_with(10)


class TestProvideUploadContentTypeSubscriber:
    """Test ProvideUploadContentTypeSubscriber."""

    def test_on_queued(self) -> None:
        """Test on_queued."""
        future = FakeTransferFuture(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(fileobj="test.txt")
            )
        )
        assert not ProvideUploadContentTypeSubscriber().on_queued(future)  # type: ignore
        assert future.meta.call_args.extra_args.get("ContentType") == "text/plain"


class TestRequestParamsMapper:
    """Test RequestParamsMapper."""

    params: ClassVar[Dict[str, str]] = {
        "sse": "AES256",
        "sse_kms_key_id": "my-kms-key",
        "sse_c": "AES256",
        "sse_c_key": "my-sse-c-key",
        "sse_c_copy_source": "AES256",
        "sse_c_copy_source_key": "my-sse-c-copy-source-key",
    }

    def test_map_copy_object_params(self) -> None:
        """Test map_copy_object_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_copy_object_params(
            params, {"metadata": "something", **self.params}
        )
        assert params == {
            "CopySourceSSECustomerAlgorithm": "AES256",
            "CopySourceSSECustomerKey": "my-sse-c-copy-source-key",
            "Metadata": "something",
            "MetadataDirective": "REPLACE",
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
            "SSEKMSKeyId": "my-kms-key",
            "ServerSideEncryption": "AES256",
        }

    def test_map_copy_object_params_metadata_directive(self) -> None:
        """Test map_copy_object_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_copy_object_params(
            params, {"metadata_directive": "something", **self.params}
        )
        assert params == {
            "CopySourceSSECustomerAlgorithm": "AES256",
            "CopySourceSSECustomerKey": "my-sse-c-copy-source-key",
            "MetadataDirective": "something",
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
            "SSEKMSKeyId": "my-kms-key",
            "ServerSideEncryption": "AES256",
        }

    def test_map_create_multipart_upload_params(self) -> None:
        """Test map_create_multipart_upload_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_create_multipart_upload_params(
            params, self.params
        )
        assert params == {
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
            "SSEKMSKeyId": "my-kms-key",
            "ServerSideEncryption": "AES256",
        }

    def test_map_delete_object_params(self) -> None:
        """Test map_delete_object_params."""
        params: Dict[str, Any] = {}
        assert not RequestParamsMapper.map_delete_object_params(
            params, {"request_payer": "requester", **self.params}
        )
        assert params == {"RequestPayer": "requester"}

    def test_map_get_object_params(self) -> None:
        """Test map_get_object_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_get_object_params(params, self.params)
        assert params == {
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
        }

    def test_map_head_object_params(self) -> None:
        """Test map_head_object_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_head_object_params(params, self.params)
        assert params == {
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
        }

    def test_map_list_objects_v2_params(self) -> None:
        """Test map_list_objects_v2_params."""
        params: Dict[str, Any] = {}
        assert not RequestParamsMapper.map_list_objects_v2_params(
            params, {"request_payer": "requester", **self.params}
        )
        assert params == {"RequestPayer": "requester"}

    def test_map_put_object_params(self) -> None:
        """Test map_put_object_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_put_object_params(
            params,
            {
                "grants": [
                    "read=test-read",
                    "full=test-full",
                    "readacl=test-readacl",
                    "writeacl=test-writeacl",
                ],
                "storage_class": "default",
                **self.params,
            },
        )
        assert params == {
            "GrantFullControl": "test-full",
            "GrantRead": "test-read",
            "GrantReadACP": "test-readacl",
            "GrantWriteACP": "test-writeacl",
            "ServerSideEncryption": "AES256",
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
            "SSEKMSKeyId": "my-kms-key",
            "StorageClass": "default",
        }

    def test_map_put_object_params_raise_value_error_format(self) -> None:
        """Test map_put_object_params."""
        params: Dict[str, str] = {}
        with pytest.raises(ValueError) as excinfo:
            RequestParamsMapper.map_put_object_params(
                params, {"grants": ["invalid"], **self.params}
            )
        assert str(excinfo.value) == "grants should be of the form permission=principal"

    def test_map_put_object_params_raise_value_error_permission(self) -> None:
        """Test map_put_object_params."""
        params: Dict[str, str] = {}
        with pytest.raises(ValueError) as excinfo:
            RequestParamsMapper.map_put_object_params(
                params, {"grants": ["invalid=test-read"], **self.params}
            )
        assert (
            str(excinfo.value)
            == "permission must be one of: read|readacl|writeacl|full"
        )

    def test_map_upload_part_params(self) -> None:
        """Test map_upload_part_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_upload_part_params(params, self.params)
        assert params == {
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
        }

    def test_map_upload_part_copy_params(self) -> None:
        """Test map_upload_part_copy_params."""
        params: Dict[str, str] = {}
        assert not RequestParamsMapper.map_upload_part_copy_params(params, self.params)
        assert params == {
            "CopySourceSSECustomerAlgorithm": "AES256",
            "CopySourceSSECustomerKey": "my-sse-c-copy-source-key",
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "my-sse-c-key",
        }


class TestStdoutBytesWriter:
    """Test StdoutBytesWriter."""

    def test_write(self) -> None:
        """Test write."""
        stdout = Mock(buffer=None)
        wrapper = StdoutBytesWriter(stdout)
        wrapper.write(b"foo")
        assert stdout.write.called
        assert stdout.write.call_args[0][0] == "foo"

    def test_write_buffer(self) -> None:
        """Test write."""
        buffer = Mock()
        stdout = Mock()
        stdout.buffer = buffer
        wrapper = StdoutBytesWriter(stdout)
        wrapper.write(b"foo")
        assert buffer.write.called
        assert buffer.write.call_args[0][0] == b"foo"

    def test_write_no_stdout(self, mocker: MockerFixture) -> None:
        """Test write."""
        stdout = mocker.patch("sys.stdout", Mock(buffer=None))
        wrapper = StdoutBytesWriter()
        wrapper.write(b"foo")
        assert stdout.write.called
        assert stdout.write.call_args[0][0] == "foo"


def test_block_s3_object_lambda_raise_colon() -> None:
    """Test block_s3_object_lambda."""
    with pytest.raises(ValueError) as excinfo:
        block_s3_object_lambda(
            "arn:aws:s3-object-lambda:us-west-2:123456789012:"
            "accesspoint:my-accesspoint"
        )
    assert "does not support S3 Object Lambda resources" in str(excinfo.value)


def test_block_s3_object_lambda_raise_slash() -> None:
    """Test block_s3_object_lambda."""
    with pytest.raises(ValueError) as excinfo:
        block_s3_object_lambda(
            "arn:aws:s3-object-lambda:us-west-2:123456789012:"
            "accesspoint/my-accesspoint"
        )
    assert "does not support S3 Object Lambda resources" in str(excinfo.value)


def test_create_warning() -> None:
    """Test create_warning."""
    path = "/test.txt"
    error_message = "There was an error"
    result = create_warning(path, error_message, False)
    assert isinstance(result, PrintTask)
    assert result.message == f"warning: {error_message}"
    assert not result.error
    assert result.warning


def test_create_warning_skip_file() -> None:
    """Test create_warning."""
    path = "/test.txt"
    error_message = "There was an error"
    result = create_warning(path, error_message)
    assert isinstance(result, PrintTask)
    assert result.message == f"warning: skipping file {path}; {error_message}"
    assert not result.error
    assert result.warning


def test_date_parser() -> None:
    """Test _date_parser."""
    now = datetime.datetime.now(tzlocal())
    assert _date_parser(now.isoformat()) == now


def test_date_parser_datetime() -> None:
    """Test _date_parser."""
    now = datetime.datetime.now()
    assert _date_parser(now) == now


@pytest.mark.parametrize(
    "provided, bucket, key",
    [
        ("\u1234/\u5678", "\u1234", "\u5678"),
        ("bucket", "bucket", ""),
        ("bucket/", "bucket", ""),
        ("bucket/key", "bucket", "key"),
        ("bucket/prefix/key", "bucket", "prefix/key"),
        (
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint",
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint",
            "",
        ),
        (
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/",
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint",
            "",
        ),
        (
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/key",
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint",
            "key",
        ),
        (
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/pre/key",
            "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint",
            "pre/key",
        ),
        (
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "",
        ),
        (
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint/key",
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "key",
        ),
        (
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint/key:name",
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "key:name",
        ),
        (
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint/key/name",
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "key/name",
        ),
        (
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint/prefix/key:name",
            "arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:accesspoint:my-accesspoint",
            "prefix/key:name",
        ),
    ],
)
def test_find_bucket_key(bucket: str, key: str, provided: str) -> None:
    """Test find_bucket_key."""
    assert find_bucket_key(provided) == (bucket, key)


def test_find_dest_path_comp_key_locals3_dir(tmp_path: Path) -> None:
    """Test find_dest_path_comp_key."""
    dest = "test-bucket/prefix/"
    files = FormatPathResult(
        dest=FormattedPathDetails(path="test-bucket/prefix/", type="s3"),
        dir_op=True,
        src=FormattedPathDetails(path=f"{tmp_path}{os.sep}", type="local"),
        use_src_name=True,
    )
    src_path = tmp_path / "something"
    src_path.mkdir(parents=True)
    dest_path, compare_key = find_dest_path_comp_key(files, src_path)
    assert dest_path == f"{dest}something/"
    assert compare_key == "something/"


def test_find_dest_path_comp_key_locals3_file(tmp_path: Path) -> None:
    """Test find_dest_path_comp_key."""
    dest = "test-bucket/prefix/"
    file_path = "something/test.txt"
    src_path = tmp_path / file_path
    files = FormatPathResult(
        dest=FormattedPathDetails(path=dest, type="s3"),
        dir_op=True,
        src=FormattedPathDetails(path=f"{tmp_path}{os.sep}", type="local"),
        use_src_name=True,
    )
    dest_path, compare_key = find_dest_path_comp_key(files, src_path)
    assert dest_path == f"{dest}{file_path}"
    assert compare_key == file_path


def test_find_dest_path_comp_key_locals3_file_no_dir_op(tmp_path: Path) -> None:
    """Test find_dest_path_comp_key."""
    dest = "test-bucket/prefix/"
    file_path = "something/test.txt"
    src_path = tmp_path / file_path
    files = FormatPathResult(
        dest=FormattedPathDetails(path=dest + file_path, type="s3"),
        dir_op=False,
        src=FormattedPathDetails(path=str(src_path), type="local"),
        use_src_name=False,
    )
    dest_path, compare_key = find_dest_path_comp_key(files, None)
    assert dest_path == dest + file_path
    assert compare_key == "test.txt"


def test_get_file_stat(tmp_path: Path) -> None:
    """Test get_file_stat."""
    tmp_file = tmp_path / "test.txt"
    now = datetime.datetime.now(tzlocal())
    epoch_now = time.mktime(now.timetuple())
    tmp_file.write_text("foo")
    size, update_time = get_file_stat(tmp_file)
    assert size == 3
    assert time.mktime(update_time.timetuple()) == epoch_now  # type: ignore


@pytest.mark.parametrize("exc", [ValueError(), OSError(), OverflowError()])
def test_get_file_stat_handle_timestamp_error(
    exc: Exception, mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test get_file_stat."""
    mocker.patch(f"{MODULE}.datetime", fromtimestamp=Mock(side_effect=exc))
    tmp_file = tmp_path / "test.txt"
    tmp_file.write_text("foo")
    assert get_file_stat(tmp_file) == (3, None)


def test_get_file_stat_raise_value_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test get_file_stat."""
    mocker.patch.object(Path, "stat", PropertyMock(side_effect=IOError("msg")))
    tmp_file = tmp_path / "test.txt"
    with pytest.raises(ValueError) as excinfo:
        get_file_stat(tmp_file)
    assert str(excinfo.value) == f"Could not retrieve file stat of {tmp_file}: msg"


def test_guess_content_type(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test guess_content_type."""
    mock_guess_type = Mock(return_value=("something",))
    mocker.patch(f"{MODULE}.mimetypes", guess_type=mock_guess_type)
    tmp_file = tmp_path / "test.txt"
    assert guess_content_type(tmp_file) == "something"
    mock_guess_type.assert_called_once_with(str(tmp_file))
    assert guess_content_type(tmp_file.name) == "something"
    mock_guess_type.assert_called_with(tmp_file.name)


def test_guess_content_type_handle_unicode_decode_error(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test guess_content_type."""
    mocker.patch(
        f"{MODULE}.mimetypes",
        guess_type=Mock(side_effect=UnicodeDecodeError("", b"", 0, 0, "")),
    )
    assert not guess_content_type(tmp_path / "test.txt")


@pytest.mark.parametrize(
    "value, expected",
    [
        (1, "1 Byte"),
        (10, "10 Bytes"),
        (1000, "1000 Bytes"),
        (1024, "1.0 KiB"),
        (1024**2, "1.0 MiB"),
        (1024**3, "1.0 GiB"),
        (1024**4, "1.0 TiB"),
        (1024**5, "1.0 PiB"),
        (1024**6, "1.0 EiB"),
        (1024**2 - 1, "1.0 MiB"),
        (1024**3 - 1, "1.0 GiB"),
        (1024**7, None),
    ],
)
def test_human_readable_size(expected: Optional[str], value: float) -> None:
    """Test human_readable_size."""
    assert human_readable_size(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", 1),
        ("10", 10),
        ("1000", 1000),
        ("1KB", 1024),
        ("1kb", 1024),
        ("1KiB", 1024),
        ("1MB", 1024**2),
        ("1MiB", 1024**2),
        ("1GB", 1024**3),
        ("1GiB", 1024**3),
        ("1TB", 1024**4),
        ("1TiB", 1024**4),
    ],
)
def test_human_readable_to_bytes(expected: int, value: str) -> None:
    """Test human_readable_to_bytes."""
    assert human_readable_to_bytes(value) == expected


def test_human_readable_to_bytes_raise_value_error() -> None:
    """Test human_readable_to_bytes."""
    with pytest.raises(ValueError) as excinfo:
        human_readable_to_bytes("test")
    assert str(excinfo.value) == "Invalid size value: test"


@pytest.mark.skipif(
    platform.system() == "Windows", reason="crashes xdist worker on Windows"
)
def test_relative_path_handle_value_error(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test relative_path."""
    tmp_file = tmp_path / "test.txt"
    mocker.patch("os.path.split", side_effect=ValueError())
    result = relative_path(tmp_file, tmp_path)
    assert isinstance(result, str)
    assert os.path.isabs(result)


@pytest.mark.parametrize(
    "filename, start, expected",
    [("/tmp/foo/bar", "/tmp/foo", f".{os.sep}bar"), (None, "/foo", None)],
)
def test_relative_path_posix(
    expected: Optional[str], filename: Optional[str], mocker: MockerFixture, start: str
) -> None:
    """Test relative_path."""
    mocker.patch("os.path.relpath", posixpath.relpath)
    mocker.patch("os.path.split", posixpath.split)
    assert relative_path(filename, start) == expected


@pytest.mark.parametrize(
    "filename, start, expected",
    [(None, "/foo", None), (r"C:\tmp\foo\bar", r"C:\tmp\foo", f".{os.sep}bar")],
)
def test_relative_path_windows(
    expected: Optional[str], filename: Optional[str], mocker: MockerFixture, start: str
) -> None:
    """Test relative_path."""
    mocker.patch("os.path.relpath", ntpath.relpath)
    mocker.patch("os.path.split", ntpath.split)
    assert relative_path(filename, start) == expected


def test_set_file_utime(tmp_path: Path) -> None:
    """Test set_file_utime."""
    tmp_file = tmp_path / "test.txt"
    tmp_file.touch()
    now = datetime.datetime.now(tzlocal())
    epoch_now = time.mktime(now.timetuple())
    assert not set_file_utime(tmp_file, epoch_now)
    _, update_time = get_file_stat(tmp_file)
    assert time.mktime(update_time.timetuple()) == epoch_now  # type: ignore


def test_set_file_utime_handle_errno_1(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test set_file_utime."""
    tmp_file = tmp_path / "test.txt"
    mocker.patch("os.utime", side_effect=OSError(1, ""))
    now = datetime.datetime.now(tzlocal())
    epoch_now = time.mktime(now.timetuple())
    with pytest.raises(SetFileUtimeError) as excinfo:
        set_file_utime(tmp_file, epoch_now)
    assert "attempting to modify the utime of the file failed" in str(excinfo.value)


def test_set_file_utime_raise_os_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test set_file_utime."""
    tmp_file = tmp_path / "test.txt"
    mocker.patch("os.utime", side_effect=OSError(2, ""))
    now = datetime.datetime.now(tzlocal())
    epoch_now = time.mktime(now.timetuple())
    with pytest.raises(OSError):
        set_file_utime(tmp_file, epoch_now)


def test_uni_print() -> None:
    """Test uni_print."""
    out_file = Mock()
    assert not uni_print("test", out_file)
    out_file.write.assert_called_once_with("test")
    out_file.flush.assert_called_once_with()


def test_uni_print_handle_unicode_encoding_error() -> None:
    """Test uni_print."""
    out_file = Mock(
        encoding=None,
        write=Mock(
            side_effect=[UnicodeEncodeError("test", "test", 0, 0, "test"), None]
        ),
    )
    assert not uni_print("test", out_file)
    assert out_file.write.call_count == 2
    out_file.flush.assert_called_once_with()


def test_uni_print_no_out_file(mocker: MockerFixture) -> None:
    """Test uni_print."""
    out_file = mocker.patch("sys.stdout")
    assert not uni_print("test")
    out_file.write.assert_called_once_with("test")
    out_file.flush.assert_called_once_with()
