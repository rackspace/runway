"""Test runway.core.providers.aws.s3._helpers.s3handler."""

# pylint: disable=redefined-outer-name,too-many-lines
from __future__ import annotations

from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Any, ClassVar, Dict, NamedTuple, Optional, cast

import pytest
from mock import MagicMock, Mock
from s3transfer.manager import TransferManager

from runway.core.providers.aws.s3._helpers.file_info import FileInfo
from runway.core.providers.aws.s3._helpers.parameters import ParametersDataModel
from runway.core.providers.aws.s3._helpers.results import (
    CommandResultRecorder,
    CopyResultSubscriber,
    DeleteResultSubscriber,
    DownloadResultSubscriber,
    DownloadStreamResultSubscriber,
    DryRunResult,
    FailureResult,
    NoProgressResultPrinter,
    OnlyShowErrorsResultPrinter,
    QueuedResult,
    ResultRecorder,
    SuccessResult,
    UploadResultSubscriber,
    UploadStreamResultSubscriber,
)
from runway.core.providers.aws.s3._helpers.s3handler import (
    BaseTransferRequestSubmitter,
    CopyRequestSubmitter,
    DeleteRequestSubmitter,
    DownloadRequestSubmitter,
    DownloadStreamRequestSubmitter,
    LocalDeleteRequestSubmitter,
    S3TransferHandler,
    S3TransferHandlerFactory,
    StdinMissingError,
    UploadRequestSubmitter,
    UploadStreamRequestSubmitter,
)
from runway.core.providers.aws.s3._helpers.transfer_config import RuntimeConfig
from runway.core.providers.aws.s3._helpers.utils import (
    MAX_UPLOAD_SIZE,
    DeleteSourceFileSubscriber,
    DeleteSourceObjectSubscriber,
    DirectoryCreatorSubscriber,
    NonSeekableStream,
    PrintTask,
    ProvideCopyContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber,
    ProvideSizeSubscriber,
    ProvideUploadContentTypeSubscriber,
    StdoutBytesWriter,
)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.transfer_config import TransferConfigDict
    from runway.type_defs import AnyPath

MODULE = "runway.core.providers.aws.s3._helpers.s3handler"


class MockSubmitters(NamedTuple):
    """Named tuple return value of mock_submitters."""

    classes: Dict[str, Mock]
    instances: Dict[str, Mock]


@pytest.fixture(scope="function")
def mock_submitters(mocker: MockerFixture) -> MockSubmitters:
    """Mock handler submitters."""
    classes = {
        "copy": mocker.patch(f"{MODULE}.CopyRequestSubmitter", Mock()),
        "delete": mocker.patch(f"{MODULE}.DeleteRequestSubmitter", Mock()),
        "download": mocker.patch(f"{MODULE}.DownloadRequestSubmitter", Mock()),
        "download_stream": mocker.patch(
            f"{MODULE}.DownloadStreamRequestSubmitter", Mock()
        ),
        "local_delete": mocker.patch(f"{MODULE}.LocalDeleteRequestSubmitter", Mock()),
        "upload": mocker.patch(f"{MODULE}.UploadRequestSubmitter", Mock()),
        "upload_stream": mocker.patch(f"{MODULE}.UploadStreamRequestSubmitter", Mock()),
    }
    instances: Dict[str, Mock] = {}
    for name, mock_class in classes.items():
        inst = Mock(can_submit=Mock(return_value=False), submit=Mock(return_value=True))
        mock_class.return_value = inst
        instances[name] = inst
    return MockSubmitters(classes=classes, instances=instances)


class BaseTransferRequestSubmitterTest:
    """Base class for transfer request submitter test classes."""

    bucket: ClassVar[str] = "test-bucket"
    config_params: ParametersDataModel
    filename: ClassVar[str] = "test-file.txt"
    key: ClassVar[str] = "test-key.txt"
    result_queue: "Queue[Any]"
    transfer_manager: Mock

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.config_params = ParametersDataModel(dest="", src="")
        self.result_queue = Queue()
        self.transfer_manager = Mock(spec=TransferManager)


class TestBaseTransferRequestSubmitter:
    """Test BaseTransferRequestSubmitter."""

    def test_can_submit(self) -> None:
        """Test can_submit."""
        with pytest.raises(NotImplementedError) as excinfo:
            BaseTransferRequestSubmitter(
                Mock(name="transfer_manager"),
                Mock(name="result_queue"),
                ParametersDataModel(dest="", src=""),
            ).can_submit(Mock(name="fileinfo"))
        assert str(excinfo.value) == "can_submit()"

    @pytest.mark.parametrize(
        "path, expected",
        [
            (None, None),
            ("", None),
            (Path.cwd(), f"s3://{Path.cwd()}"),
            ("s3://test", "s3://test"),
        ],
    )
    def test_format_s3_path(
        self, expected: Optional[str], path: Optional[AnyPath]
    ) -> None:
        """Test _format_s3_path."""
        assert (
            # pylint: disable=protected-access
            BaseTransferRequestSubmitter(
                Mock(), Mock(), ParametersDataModel(dest="", src="")
            )._format_s3_path(path)
            == expected
        )

    def test_submit(self) -> None:
        """Test submit."""
        with pytest.raises(NotImplementedError) as excinfo:
            BaseTransferRequestSubmitter(
                Mock(name="transfer_manager"),
                Mock(name="result_queue"),
                ParametersDataModel(dest="", src=""),
            ).submit(Mock(name="fileinfo"))
        assert str(excinfo.value) == "_submit_transfer_request()"

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        with pytest.raises(NotImplementedError) as excinfo:
            BaseTransferRequestSubmitter(
                Mock(name="transfer_manager"),
                Mock(name="result_queue"),
                ParametersDataModel(dest="", src="", dryrun=True),
            ).submit(Mock(name="fileinfo"))
        assert str(excinfo.value) == "_format_src_dest()"


class TestCopyRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test CopyRequestSubmitter."""

    source_bucket: ClassVar[str] = "test-source-bucket"
    source_key: ClassVar[str] = "test-source-key.txt"
    transfer_request_submitter: CopyRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
            operation_name="copy",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        fileinfo.operation_name = "foo"
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
        )
        self.config_params["guess_mime_type"] = True
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.copy.return_value is future
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.copy.call_args[1])
        assert call_kwargs["copy_source"] == {
            "Bucket": self.source_bucket,
            "Key": self.source_key,
        }
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}

        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideCopyContentTypeSubscriber,
            CopyResultSubscriber,
        ]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_content_type_specified(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
        )
        self.config_params["content_type"] = "text/plain"
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = cast(Dict[str, Any], self.transfer_manager.copy.call_args[1])
        assert copy_call_kwargs["extra_args"] == {"ContentType": "text/plain"}
        ref_subscribers = [ProvideSizeSubscriber, CopyResultSubscriber]
        actual_subscribers = copy_call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            src_type="s3",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
            operation_name="copy",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "copy"
        source = "s3://" + self.source_bucket + "/" + self.source_key
        assert result.src == source
        assert result.dest == "s3://" + self.bucket + "/" + self.key

    def test_submit_extra_args(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
        )
        self.config_params["storage_class"] = "STANDARD_IA"
        self.transfer_request_submitter.submit(fileinfo)

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.copy.call_args[1])
        assert call_kwargs["extra_args"] == {"StorageClass": "STANDARD_IA"}

    def test_submit_move_adds_delete_source_subscriber(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            dest=self.source_bucket + "/" + self.source_key,
            src=self.bucket + "/" + self.key,
        )
        self.config_params["guess_mime_type"] = True  # Default settings
        self.config_params["is_move"] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideCopyContentTypeSubscriber,
            DeleteSourceObjectSubscriber,
            CopyResultSubscriber,
        ]
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.copy.call_args[1])
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_no_guess_content_mime_type(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
        )
        self.config_params["guess_mime_type"] = False
        self.transfer_request_submitter.submit(fileinfo)
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.copy.call_args[1])
        ref_subscribers = [ProvideSizeSubscriber, CopyResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_warn_glacier_force(self) -> None:
        """Test submit."""
        self.config_params["force_glacier_transfer"] = True
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
            operation_name="copy",
            response_data={"StorageClass": "GLACIER"},
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.copy.return_value is future
        assert self.result_queue.empty()
        assert len(self.transfer_manager.copy.call_args_list) == 1  # type: ignore

    def test_submit_warn_glacier_ignore_warning(self) -> None:
        """Test submit."""
        self.config_params["ignore_glacier_warnings"] = True
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
            operation_name="copy",
            response_data={"StorageClass": "GLACIER"},
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert future is None
        assert self.result_queue.empty()
        assert len(self.transfer_manager.copy.call_args_list) == 0  # type: ignore

    def test_submit_warn_glacier_incompatible(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
            operation_name="copy",
            response_data={"StorageClass": "GLACIER"},
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        warning_result = self.result_queue.get()
        assert isinstance(warning_result, PrintTask)
        assert (
            "Unable to perform copy operations on GLACIER objects"
            in warning_result.message
        )
        assert future is None
        assert len(self.transfer_manager.copy.call_args_list) == 0  # type: ignore


class TestDeleteRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test DeleteRequestSubmitter."""

    transfer_request_submitter: DeleteRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.transfer_request_submitter = DeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=None,
            operation_name="delete",
            src_type="s3",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        fileinfo.operation_name = "foo"
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_can_submit_local_delete(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=None,
            operation_name="delete",
            src_type="local",
        )
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key, dest=None, operation_name="delete"
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.delete.return_value is future

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.delete.call_args[1])
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}

        ref_subscribers = [DeleteResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        self.transfer_request_submitter = DeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            src_type="s3",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
            operation_name="delete",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "delete"
        assert result.src == "s3://" + self.bucket + "/" + self.key
        assert not result.dest


class TestDownloadRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test DownloadRequestSubmitter."""

    transfer_request_submitter: DownloadRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def assert_no_downloads_happened(self) -> None:
        """Assert not downloads."""
        assert len(self.transfer_manager.download.call_args_list) == 0  # type: ignore

    def create_file_info(
        self, key: str, response_data: Optional[Dict[str, Any]] = None
    ) -> FileInfo:
        """Create FileInfo."""
        kwargs: Dict[str, Any] = {
            "src": self.bucket + "/" + key,
            "src_type": "s3",
            "dest": self.filename,
            "dest_type": "local",
            "operation_name": "download",
            "compare_key": key,
        }
        if response_data is not None:
            kwargs["response_data"] = response_data
        return FileInfo(**kwargs)

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=self.filename,
            operation_name="download",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        fileinfo.operation_name = "foo"
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info(self.key)
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.download.return_value is future
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.download.call_args[1])
        assert call_kwargs["fileobj"] == self.filename
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}
        ref_subscribers = [
            ProvideSizeSubscriber,
            DirectoryCreatorSubscriber,
            ProvideLastModifiedTimeSubscriber,
            DownloadResultSubscriber,
        ]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_allow_double_dots_no_escape(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        fileinfo = self.create_file_info("a/../foo.txt")
        self.transfer_request_submitter.submit(fileinfo)
        assert isinstance(self.result_queue.get(), DryRunResult)

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )
        fileinfo = self.create_file_info(self.key)
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "download"
        assert result.dest.endswith(self.filename)  # type: ignore
        assert result.src == "s3://" + self.bucket + "/" + self.key

    def test_submit_extra_args(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info(self.key)
        self.config_params["sse_c"] = "AES256"
        self.config_params["sse_c_key"] = "test-key"
        self.transfer_request_submitter.submit(fileinfo)
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.download.call_args[1])
        assert call_kwargs["extra_args"] == {
            "SSECustomerAlgorithm": "AES256",
            "SSECustomerKey": "test-key",
        }

    def test_submit_move_adds_delete_source_subscriber(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info(self.key)
        self.config_params["guess_mime_type"] = True
        self.config_params["is_move"] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            DirectoryCreatorSubscriber,
            ProvideLastModifiedTimeSubscriber,
            DeleteSourceObjectSubscriber,
            DownloadResultSubscriber,
        ]
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.download.call_args[1])
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_no_warn_glacier_for_compatible(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info(
            self.key,
            response_data={
                "StorageClass": "GLACIER",
                "Restore": 'ongoing-request="false"',
            },
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.result_queue.empty()
        assert self.transfer_manager.download.return_value is future
        assert len(self.transfer_manager.download.call_args_list) == 1  # type: ignore

    def test_submit_warn_and_ignore_on_parent_dir_reference(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info("../foo.txt")
        self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        assert isinstance(warning_result, PrintTask)
        self.assert_no_downloads_happened()

    def test_warn_and_ignore_with_leading_chars(self) -> None:
        """Test submit."""
        fileinfo = self.create_file_info("a/../../foo.txt")
        self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        assert isinstance(warning_result, PrintTask)
        self.assert_no_downloads_happened()

    def test_submit_warn_glacier_force(self) -> None:
        """Test submit."""
        self.config_params["force_glacier_transfer"] = True
        fileinfo = self.create_file_info(
            self.key, response_data={"StorageClass": "GLACIER"}
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.result_queue.empty()
        assert self.transfer_manager.download.return_value is future
        assert len(self.transfer_manager.download.call_args_list) == 1  # type: ignore

    def test_warn_glacier_ignore_warning(self) -> None:
        """Test submit."""
        self.config_params["ignore_glacier_warnings"] = True
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=self.filename,
            operation_name="download",
            response_data={"StorageClass": "GLACIER"},
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.result_queue.empty()
        assert not future
        self.assert_no_downloads_happened()

    def test_submit_warn_glacier_incompatible(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=self.filename,
            operation_name="download",
            response_data={"StorageClass": "GLACIER"},
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        assert isinstance(warning_result, PrintTask)
        assert (
            "Unable to perform download operations on GLACIER objects"
            in warning_result.message
        )
        assert not future
        self.assert_no_downloads_happened()


class TestDownloadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test DownloadStreamRequestSubmitter."""

    filename: ClassVar[str] = "-"
    transfer_request_submitter: DownloadStreamRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.config_params["is_stream"] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key,
            dest=self.filename,
            operation_name="download",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        self.config_params["is_stream"] = False
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.bucket + "/" + self.key, dest=self.filename, compare_key=self.key
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.download.return_value is future

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.download.call_args[1])
        assert isinstance(call_kwargs["fileobj"], StdoutBytesWriter)
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}

        ref_subscribers = [DownloadStreamResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        fileinfo = FileInfo(
            dest=self.filename,
            dest_type="local",
            operation_name="download",
            src=self.bucket + "/" + self.key,
            src_type="s3",
            compare_key=self.key,
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "download"
        assert result.src == "s3://" + self.bucket + "/" + self.key
        assert result.dest == "-"


class TestLocalDeleteRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test LocalDeleteRequestSubmitter."""

    transfer_request_submitter: LocalDeleteRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.transfer_request_submitter = LocalDeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name="delete", src_type="local"
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        fileinfo.operation_name = "foo"
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_can_submit_remote_deletes(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name="delete", src_type="s3"
        )
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self, tmp_path: Path) -> None:
        """Test submit."""
        full_filename = tmp_path / self.filename
        full_filename.write_text("content")
        fileinfo = FileInfo(
            src=full_filename, dest=None, operation_name="delete", src_type="local"
        )
        result = self.transfer_request_submitter.submit(fileinfo)
        assert result
        queued_result = self.result_queue.get()
        assert isinstance(queued_result, QueuedResult)
        assert queued_result.transfer_type == "delete"
        assert queued_result.src.endswith(self.filename)  # type: ignore
        assert queued_result.dest is None
        assert queued_result.total_transfer_size == 0

        failure_result = self.result_queue.get()
        assert isinstance(failure_result, SuccessResult)
        assert failure_result.transfer_type == "delete"
        assert failure_result.src.endswith(self.filename)  # type: ignore
        assert failure_result.dest is None
        assert not full_filename.exists()

    def test_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        fileinfo = FileInfo(
            src=self.filename,
            src_type="local",
            dest=self.filename,
            dest_type="local",
            operation_name="delete",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "delete"
        assert result.src.endswith(self.filename)  # type: ignore
        assert result.dest is None

    def test_submit_with_exception(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name="delete", src_type="local"
        )
        result = self.transfer_request_submitter.submit(fileinfo)
        assert result

        queued_result = self.result_queue.get()
        assert isinstance(queued_result, QueuedResult)
        assert queued_result.transfer_type == "delete"
        assert queued_result.src.endswith(self.filename)  # type: ignore
        assert queued_result.dest is None
        assert queued_result.total_transfer_size == 0

        failure_result = self.result_queue.get()
        assert isinstance(failure_result, FailureResult)
        assert failure_result.transfer_type == "delete"
        assert failure_result.src.endswith(self.filename)  # type: ignore
        assert failure_result.dest is None


class TestS3TransferHandler:
    """Test S3TransferHandler."""

    config_params: ClassVar[ParametersDataModel] = ParametersDataModel(dest="", src="")
    result_command_recorder: CommandResultRecorder
    result_queue: "Queue[Any]"
    transfer_manager: TransferManager

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_queue = Mock(spec=Queue)
        self.result_command_recorder = MagicMock(
            spec=CommandResultRecorder, result_queue=self.result_queue
        )
        self.transfer_manager = MagicMock(spec=TransferManager)

    def test_call(self, mock_submitters: MockSubmitters, tmp_path: Path) -> None:
        """Test call."""
        mock_submitters.instances["copy"].can_submit.return_value = True
        mock_submitters.instances["delete"].can_submit.return_value = True
        self.result_command_recorder.get_command_result.return_value = "success"  # type: ignore
        handler = S3TransferHandler(
            self.transfer_manager, self.config_params, self.result_command_recorder
        )
        fileinfos = [FileInfo(src=tmp_path)]
        assert handler.call(fileinfos) == "success"  # type: ignore
        mock_submitters.instances["copy"].can_submit.assert_called_once_with(
            fileinfos[0]
        )
        mock_submitters.instances["copy"].submit.assert_called_once_with(fileinfos[0])
        self.result_command_recorder.notify_total_submissions.assert_called_once_with(1)  # type: ignore
        self.result_command_recorder.get_command_result.assert_called_once_with()  # type: ignore


class TestS3TransferHandlerFactory:
    """Test S3TransferHandlerFactory."""

    config_params: ParametersDataModel
    client: S3Client
    result_queue: "Queue[Any]"
    runtime_config: TransferConfigDict

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.config_params = ParametersDataModel(dest="", src="")
        self.client = Mock()
        self.result_queue = Queue()
        self.runtime_config = RuntimeConfig.build_config()

    def test_call(self) -> None:
        """Test __call__."""
        factory = S3TransferHandlerFactory(self.config_params, self.runtime_config)
        assert isinstance(factory(self.client, self.result_queue), S3TransferHandler)

    def test_call_is_stream(self, mocker: MockerFixture) -> None:
        """Test __call__."""
        mock_processor = mocker.patch(f"{MODULE}.ResultProcessor")
        self.config_params["is_stream"] = True
        assert S3TransferHandlerFactory(self.config_params, self.runtime_config)(
            self.client, self.result_queue
        )
        call_kwargs = cast(Dict[str, Any], mock_processor.call_args[1])
        assert len(call_kwargs["result_handlers"]) == 2
        assert isinstance(call_kwargs["result_handlers"][0], ResultRecorder)
        assert isinstance(
            call_kwargs["result_handlers"][1], OnlyShowErrorsResultPrinter
        )

    def test_call_no_progress(self, mocker: MockerFixture) -> None:
        """Test __call__."""
        mock_processor = mocker.patch(f"{MODULE}.ResultProcessor")
        self.config_params["no_progress"] = True
        assert S3TransferHandlerFactory(self.config_params, self.runtime_config)(
            self.client, self.result_queue
        )
        call_kwargs = cast(Dict[str, Any], mock_processor.call_args[1])
        assert len(call_kwargs["result_handlers"]) == 2
        assert isinstance(call_kwargs["result_handlers"][0], ResultRecorder)
        assert isinstance(call_kwargs["result_handlers"][1], NoProgressResultPrinter)

    def test_call_only_show_errors(self, mocker: MockerFixture) -> None:
        """Test __call__."""
        mock_processor = mocker.patch(f"{MODULE}.ResultProcessor")
        self.config_params["only_show_errors"] = True
        assert S3TransferHandlerFactory(self.config_params, self.runtime_config)(
            self.client, self.result_queue
        )
        call_kwargs = cast(Dict[str, Any], mock_processor.call_args[1])
        assert len(call_kwargs["result_handlers"]) == 2
        assert isinstance(call_kwargs["result_handlers"][0], ResultRecorder)
        assert isinstance(
            call_kwargs["result_handlers"][1], OnlyShowErrorsResultPrinter
        )

    def test_call_quiet(self, mocker: MockerFixture) -> None:
        """Test __call__."""
        mock_processor = mocker.patch(f"{MODULE}.ResultProcessor")
        self.config_params["quiet"] = True
        assert S3TransferHandlerFactory(self.config_params, self.runtime_config)(
            self.client, self.result_queue
        )
        call_kwargs = cast(Dict[str, Any], mock_processor.call_args[1])
        assert len(call_kwargs["result_handlers"]) == 1
        assert isinstance(call_kwargs["result_handlers"][0], ResultRecorder)


class TestUploadRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test UploadRequestSubmitter."""

    transfer_request_submitter: UploadRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.filename,
            dest=self.bucket + "/" + self.key,
            operation_name="upload",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        fileinfo.operation_name = "foo"
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.config_params["guess_mime_type"] = True
        future = self.transfer_request_submitter.submit(fileinfo)

        assert self.transfer_manager.upload.return_value is future
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        assert call_kwargs["fileobj"] == self.filename
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}

        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideUploadContentTypeSubscriber,
            UploadResultSubscriber,
        ]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_content_type_specified(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.config_params["content_type"] = "text/plain"
        self.transfer_request_submitter.submit(fileinfo)

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        assert call_kwargs["extra_args"] == {"ContentType": "text/plain"}
        ref_subscribers = [ProvideSizeSubscriber, UploadResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )
        fileinfo = FileInfo(
            src=self.filename,
            src_type="local",
            operation_name="upload",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "upload"
        assert result.src.endswith(self.filename)  # type: ignore
        assert result.dest == "s3://" + self.bucket + "/" + self.key

    def test_dry_run_move(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        self.config_params["is_move"] = True
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )
        fileinfo = FileInfo(
            src=self.filename,
            src_type="local",
            operation_name="upload",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "move"

    def test_submit_extra_args(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.config_params["storage_class"] = "STANDARD_IA"
        self.transfer_request_submitter.submit(fileinfo)

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        assert call_kwargs["extra_args"] == {"StorageClass": "STANDARD_IA"}

    def test_submit_move_adds_delete_source_subscriber(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.config_params["guess_mime_type"] = True
        self.config_params["is_move"] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideUploadContentTypeSubscriber,
            DeleteSourceFileSubscriber,
            UploadResultSubscriber,
        ]
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_no_guess_content_mime_type(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.config_params["guess_mime_type"] = False
        self.transfer_request_submitter.submit(fileinfo)

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        ref_subscribers = [ProvideSizeSubscriber, UploadResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_warn_too_large_transfer(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(
            src=self.filename,
            dest=self.bucket + "/" + self.key,
            size=MAX_UPLOAD_SIZE + 1,
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        warning_result = self.result_queue.get()
        assert isinstance(warning_result, PrintTask)
        assert "exceeds s3 upload limit" in warning_result.message
        assert self.transfer_manager.upload.return_value is future
        assert len(self.transfer_manager.upload.call_args_list) == 1  # type: ignore


class TestUploadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    """Test UploadStreamRequestSubmitter."""

    filename: ClassVar[str] = "-"
    transfer_request_submitter: UploadStreamRequestSubmitter

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.config_params["is_stream"] = True
        self.transfer_request_submitter = UploadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.config_params
        )

    def test_can_submit(self) -> None:
        """Test can_submit."""
        fileinfo = FileInfo(
            src=self.filename,
            dest=self.bucket + "/" + self.key,
            operation_name="upload",
        )
        assert self.transfer_request_submitter.can_submit(fileinfo)
        self.config_params["is_stream"] = False
        assert not self.transfer_request_submitter.can_submit(fileinfo)

    def test_submit(self) -> None:
        """Test submit."""
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        future = self.transfer_request_submitter.submit(fileinfo)
        assert self.transfer_manager.upload.return_value is future

        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])
        assert isinstance(call_kwargs["fileobj"], NonSeekableStream)
        assert call_kwargs["bucket"] == self.bucket
        assert call_kwargs["key"] == self.key
        assert call_kwargs["extra_args"] == {}

        ref_subscribers = [UploadStreamResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])

    def test_submit_dry_run(self) -> None:
        """Test submit."""
        self.config_params["dryrun"] = True
        fileinfo = FileInfo(
            src=self.filename,
            src_type="local",
            operation_name="upload",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        assert isinstance(result, DryRunResult)
        assert result.transfer_type == "upload"
        assert result.dest == "s3://" + self.bucket + "/" + self.key
        assert result.src == "-"

    def test_submit_expected_size_provided(self) -> None:
        """Test submit."""
        provided_size = 100
        self.config_params["expected_size"] = provided_size
        fileinfo = FileInfo(src=self.filename, dest=self.bucket + "/" + self.key)
        self.transfer_request_submitter.submit(fileinfo)
        call_kwargs = cast(Dict[str, Any], self.transfer_manager.upload.call_args[1])

        ref_subscribers = [ProvideSizeSubscriber, UploadStreamResultSubscriber]
        actual_subscribers = call_kwargs["subscribers"]
        assert len(ref_subscribers) == len(actual_subscribers)
        for i, actual_subscriber in enumerate(actual_subscribers):
            assert isinstance(actual_subscriber, ref_subscribers[i])
        assert actual_subscribers[0].size == provided_size

    def test_submit_raise_stdin_missing(self, mocker: MockerFixture) -> None:
        """Test submit."""
        mocker.patch("sys.stdin", None)
        fileinfo = FileInfo(
            src=self.filename,
            src_type="local",
            operation_name="upload",
            dest=self.bucket + "/" + self.key,
            dest_type="s3",
        )
        with pytest.raises(StdinMissingError) as excinfo:
            self.transfer_request_submitter.submit(fileinfo)
        assert (
            excinfo.value.message
            == "stdin is required for this operation, but is not available"
        )
