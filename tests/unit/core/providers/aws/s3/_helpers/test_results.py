"""Test runway.core.providers.aws.s3._helpers.results."""

from __future__ import annotations

import time
from concurrent.futures import CancelledError
from io import StringIO
from queue import Queue
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional

import pytest
from mock import Mock
from s3transfer.exceptions import FatalError

from runway._logging import LogLevels
from runway.core.providers.aws.s3._helpers.results import (
    AnyResult,
    BaseResultHandler,
    BaseResultSubscriber,
    CommandResult,
    CommandResultRecorder,
    CopyResultSubscriber,
    CtrlCResult,
    DeleteResultSubscriber,
    DownloadResultSubscriber,
    DownloadStreamResultSubscriber,
    DryRunResult,
    ErrorResult,
    FailureResult,
    FinalTotalSubmissionsResult,
    NoProgressResultPrinter,
    OnlyShowErrorsResultPrinter,
    ProgressResult,
    QueuedResult,
    ResultPrinter,
    ResultProcessor,
    ResultRecorder,
    ShutdownThreadRequest,
    SuccessResult,
    UploadResultSubscriber,
    UploadStreamResultSubscriber,
)
from runway.core.providers.aws.s3._helpers.utils import (
    EPOCH_TIME,
    PrintTask,
    relative_path,
)

from .factories import (
    FakeTransferFuture,
    FakeTransferFutureCallArgs,
    FakeTransferFutureMeta,
)

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture
    from s3transfer.futures import TransferFuture


class BaseResultPrinterTest:
    """Base class for result printer test classes."""

    error_file: StringIO
    out_file: StringIO
    result_printer: ResultPrinter
    result_recorder: ResultRecorder

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_recorder = ResultRecorder()
        self.out_file = StringIO()
        self.error_file = StringIO()
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=self.out_file,
            error_file=self.error_file,
        )

    def get_progress_result(self) -> ProgressResult:
        """Create progress result."""
        return ProgressResult(
            transfer_type=None,
            src=None,
            dest=None,
            bytes_transferred=None,  # type: ignore
            total_transfer_size=None,  # type: ignore
            timestamp=0,
        )


class BaseResultSubscriberTest:
    """Base class for result submitter test classes."""

    bucket: ClassVar[str] = "test-bucket"
    dest: Optional[str]
    failure_future: TransferFuture
    filename: ClassVar[str] = "test.txt"
    future: TransferFuture
    key: ClassVar[str] = "test.txt"
    ref_exception: ClassVar[Exception] = Exception()
    result_queue: "Queue[Any]"
    size: ClassVar[int] = 20 * (1024 * 1024)  # 20 MB
    src: str
    transfer_type: str

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_queue = Queue()
        self.set_ref_transfer_futures()

    def set_ref_transfer_futures(self) -> None:
        """Set reference transfer futures."""
        self.future = self.get_success_transfer_future("foo")  # type: ignore
        self.failure_future = self.get_failed_transfer_future(self.ref_exception)  # type: ignore

    def get_success_transfer_future(self, result: str) -> TransferFuture:
        """Create a success transfer future."""
        return self._get_transfer_future(result=result)  # type: ignore

    def get_failed_transfer_future(self, exception: Exception) -> TransferFuture:
        """Create a failed transfer future."""
        return self._get_transfer_future(exception=exception)  # type: ignore

    def _get_transfer_future(
        self, result: Optional[Any] = None, exception: Optional[Exception] = None
    ) -> FakeTransferFuture:
        call_args = self._get_transfer_future_call_args()
        meta = FakeTransferFutureMeta(size=self.size, call_args=call_args)
        return FakeTransferFuture(result=result, exception=exception, meta=meta)

    def _get_transfer_future_call_args(self) -> FakeTransferFutureCallArgs:
        return FakeTransferFutureCallArgs(
            fileobj=self.filename, key=self.key, bucket=self.bucket
        )

    def get_queued_result(self) -> AnyResult:
        """Get queued result."""
        return self.result_queue.get(block=False)

    def assert_result_queue_is_empty(self) -> None:
        """Assert queue is empty."""
        assert self.result_queue.empty()


class TestUploadResultSubscriber(BaseResultSubscriberTest):
    """Test UploadResultSubscriber."""

    result_subscriber: BaseResultSubscriber

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.dest = "s3://" + self.bucket + "/" + self.key
        self.src = relative_path(self.filename)
        self.result_subscriber = UploadResultSubscriber(self.result_queue)
        self.transfer_type = "upload"

    def test_on_done_cancelled_for_ctrl_c(self) -> None:
        """Test on_queued progress."""
        self.result_subscriber.on_queued(self.future)
        assert self.get_queued_result() == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        self.assert_result_queue_is_empty()
        cancelled_exception = CancelledError("KeyboardInterrupt()")
        cancelled_future = self.get_failed_transfer_future(cancelled_exception)
        self.result_subscriber.on_done(cancelled_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == CtrlCResult(exception=cancelled_exception)

    def test_on_done_failure(self) -> None:
        """Test on_queued progress."""
        self.result_subscriber.on_queued(self.future)
        assert self.get_queued_result() == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        self.assert_result_queue_is_empty()

        self.result_subscriber.on_done(self.failure_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == FailureResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            exception=self.ref_exception,
        )

    def test_on_done_success(self) -> None:
        """Test on_queued progress."""
        self.result_subscriber.on_queued(self.future)
        assert self.get_queued_result() == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        self.assert_result_queue_is_empty()
        self.result_subscriber.on_done(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == SuccessResult(
            transfer_type=self.transfer_type, src=self.src, dest=self.dest
        )

    def test_on_done_unexpected_cancelled(self) -> None:
        """Test on_queued progress."""
        self.result_subscriber.on_queued(self.future)
        assert self.get_queued_result() == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        self.assert_result_queue_is_empty()
        cancelled_exception = FatalError("some error")
        cancelled_future = self.get_failed_transfer_future(cancelled_exception)
        self.result_subscriber.on_done(cancelled_future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == ErrorResult(exception=cancelled_exception)

    def test_on_queued(self) -> None:
        """Test on_queued."""
        self.result_subscriber.on_queued(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )

    def test_on_queued_progress(self) -> None:
        """Test on_queued progress."""
        self.result_subscriber.on_queued(self.future)
        assert self.get_queued_result() == QueuedResult(
            transfer_type=self.transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        self.assert_result_queue_is_empty()


class TestBaseResultHandler(BaseResultSubscriberTest):
    """Test BaseResultHandler."""

    result_subscriber: BaseResultSubscriber

    def test_call(self) -> None:
        """Test __call__."""
        with pytest.raises(NotImplementedError) as excinfo:
            BaseResultHandler()(None)
        assert str(excinfo.value) == "__call__()"

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.result_subscriber = BaseResultSubscriber(self.result_queue)

    def test_on_progress(self, mocker: MockerFixture) -> None:
        """Test on_progress."""
        mocker.patch.object(
            BaseResultSubscriber, "_get_src_dest", return_value=(None, None)
        )
        assert not self.result_subscriber.on_queued(self.future)
        assert isinstance(self.get_queued_result(), QueuedResult)
        assert not self.result_subscriber.on_progress(self.future, 13)
        result = self.get_queued_result()
        assert isinstance(result, ProgressResult)
        assert result.bytes_transferred == 13

    def test_on_queued(self) -> None:
        """Test on_queued."""
        with pytest.raises(NotImplementedError) as excinfo:
            self.result_subscriber.on_queued(self.future)
        assert str(excinfo.value) == "_get_src_dest()"


class TestBaseResultSubscriber:
    """Test BaseResultSubscriber."""


class TestCommandResultRecorder:
    """Test CommandResultRecorder."""

    command_result_recorder: CommandResultRecorder
    dest: ClassVar[str] = "s3://mybucket/test-key"
    result_processor: ResultProcessor
    result_queue: "Queue[Any]"
    result_recorder: ResultRecorder
    src: ClassVar[str] = "file"
    total_transfer_size: ClassVar[int] = 20 * (1024 * 1024)  # 20 MB
    transfer_type: ClassVar[str] = "upload"

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_queue = Queue()
        self.result_recorder = ResultRecorder()
        self.result_processor = ResultProcessor(
            self.result_queue, [self.result_recorder]
        )
        self.command_result_recorder = CommandResultRecorder(
            self.result_queue, self.result_recorder, self.result_processor
        )

    def test_error(self) -> None:
        """Test error."""
        with self.command_result_recorder:
            raise Exception("test exception")
        assert self.command_result_recorder.get_command_result() == CommandResult(
            num_tasks_failed=1, num_tasks_warned=0
        )

    def test_get_command_result_fail(self) -> None:
        """Test get_command_result."""
        with self.command_result_recorder:
            self.result_queue.put(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src,
                    dest=self.dest,
                    total_transfer_size=self.total_transfer_size,
                )
            )
            self.result_queue.put(
                FailureResult(
                    transfer_type=self.transfer_type,
                    src=self.src,
                    dest=self.dest,
                    exception=Exception("my exception"),
                )
            )
        result = self.command_result_recorder.get_command_result()
        assert result.num_tasks_failed == 1
        assert result.num_tasks_warned == 0

    def test_get_command_result_success(self) -> None:
        """Test get_command_result."""
        with self.command_result_recorder:
            self.result_queue.put(
                QueuedResult(
                    transfer_type=self.transfer_type,
                    src=self.src,
                    dest=self.dest,
                    total_transfer_size=self.total_transfer_size,
                )
            )
            self.result_queue.put(
                SuccessResult(
                    transfer_type=self.transfer_type, src=self.src, dest=self.dest
                )
            )
        result = self.command_result_recorder.get_command_result()
        assert result.num_tasks_failed == 0
        assert result.num_tasks_warned == 0

    def test_get_command_result_warning(self) -> None:
        """Test get_command_result."""
        with self.command_result_recorder:
            self.result_queue.put(PrintTask(message="my warning"))
        result = self.command_result_recorder.get_command_result()
        assert result.num_tasks_failed == 0
        assert result.num_tasks_warned == 1

    def test_notify_total_submissions(self) -> None:
        """Test get_command_result."""
        total = 5
        self.command_result_recorder.notify_total_submissions(total)
        assert self.result_queue.get() == FinalTotalSubmissionsResult(total)


class TestCopyResultSubscriber(TestUploadResultSubscriber):
    """Test CopyResultSubscriber."""

    copy_source: Dict[str, str]
    source_bucket: str
    source_key: str

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.source_bucket = "sourcebucket"
        self.source_key = "sourcekey"
        self.copy_source = {
            "Bucket": self.source_bucket,
            "Key": self.source_key,
        }
        super().setup_method()
        self.dest = "s3://" + self.bucket + "/" + self.key
        self.src = "s3://" + self.source_bucket + "/" + self.source_key
        self.transfer_type = "copy"
        self.result_subscriber = CopyResultSubscriber(self.result_queue)

    def _get_transfer_future_call_args(self) -> FakeTransferFutureCallArgs:
        return FakeTransferFutureCallArgs(
            copy_source=self.copy_source, key=self.key, bucket=self.bucket
        )

    def test_on_queued_transfer_type_override(self) -> None:
        """Test on_queued."""
        new_transfer_type = "move"
        self.result_subscriber = CopyResultSubscriber(
            self.result_queue, new_transfer_type
        )
        self.result_subscriber.on_queued(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        expected = QueuedResult(
            transfer_type=new_transfer_type,
            src=self.src,
            dest=self.dest,
            total_transfer_size=self.size,
        )
        assert result == expected


class TestDeleteResultSubscriber(TestUploadResultSubscriber):
    """Test DeleteResultSubscriber."""

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.src = "s3://" + self.bucket + "/" + self.key
        self.dest = None
        self.transfer_type = "delete"
        self.result_subscriber = DeleteResultSubscriber(self.result_queue)

    def _get_transfer_future_call_args(self) -> FakeTransferFutureCallArgs:
        return FakeTransferFutureCallArgs(bucket=self.bucket, key=self.key)


class TestDownloadResultSubscriber(TestUploadResultSubscriber):
    """Test DownloadResultSubscriber."""

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.src = "s3://" + self.bucket + "/" + self.key
        self.dest = relative_path(self.filename)
        self.transfer_type = "download"
        self.result_subscriber = DownloadResultSubscriber(self.result_queue)


class TestDownloadStreamResultSubscriber(TestDownloadResultSubscriber):
    """Test DownloadStreamResultSubscriber."""

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.dest = "-"
        self.result_subscriber = DownloadStreamResultSubscriber(self.result_queue)


class TestNoProgressResultPrinter(BaseResultPrinterTest):
    """Test NoProgressResultPrinter."""

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.result_printer = NoProgressResultPrinter(
            result_recorder=self.result_recorder,
            out_file=self.out_file,
            error_file=self.error_file,
        )

    def test_does_not_print_progress_result(self) -> None:
        """Test does not print progress result."""
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert self.out_file.getvalue() == ""

    def test_does_print_success_result(self, caplog: LogCaptureFixture) -> None:
        """Test does print success result."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert caplog.messages == ["upload: file to s3://mybucket/test-key"]
        assert self.out_file.getvalue() == ""

    def test_final_total_does_not_try_to_clear_empty_progress(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test final total does not try to clear empty progress."""
        caplog.set_level(LogLevels.INFO, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert caplog.messages == ["upload: file to s3://mybucket/test-key"]
        assert self.out_file.getvalue() == ""
        self.result_recorder.final_expected_files_transferred = 1
        self.result_printer(FinalTotalSubmissionsResult(1))
        assert caplog.messages == ["upload: file to s3://mybucket/test-key"]
        assert self.out_file.getvalue() == ""

    def test_print_failure_result(self, caplog: LogCaptureFixture) -> None:
        """Test print failure result."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert caplog.messages == [
            "upload failed: file to s3://mybucket/test-key my exception"
        ]
        assert self.error_file.getvalue() == ""

    def test_print_warning_result(self, caplog: LogCaptureFixture) -> None:
        """Test print warning."""
        caplog.set_level(LogLevels.WARNING, "runway.core.providers.aws.s3")
        self.result_printer(PrintTask("warning: my warning"))
        assert caplog.messages == ["warning: my warning"]
        assert self.error_file.getvalue() == ""


class TestOnlyShowErrorsResultPrinter(BaseResultPrinterTest):
    """Test OnlyShowErrorsResultPrinter."""

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.result_printer = OnlyShowErrorsResultPrinter(
            result_recorder=self.result_recorder,
            out_file=self.out_file,
            error_file=self.error_file,
        )

    def test_does_not_print_progress_result(self) -> None:
        """Test does not print progress result."""
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert self.out_file.getvalue() == ""

    def test_does_not_print_success_result(self, caplog: LogCaptureFixture) -> None:
        """Test does not print success result."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert not caplog.messages
        assert not self.out_file.getvalue()

    def test_does_print_failure_result(self, caplog: LogCaptureFixture) -> None:
        """Test print failure result."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert caplog.messages == [
            "upload failed: file to s3://mybucket/test-key my exception"
        ]
        assert not self.error_file.getvalue()

    def test_does_print_warning_result(self, caplog: LogCaptureFixture) -> None:
        """Test print warning."""
        caplog.set_level(LogLevels.WARNING, "runway.core.providers.aws.s3")
        self.result_printer(PrintTask("warning: my warning"))
        assert caplog.messages == ["warning: my warning"]
        assert not self.error_file.getvalue()

    def test_final_total_does_not_try_to_clear_empty_progress(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test final total does not try to clear empty progress."""
        caplog.set_level(LogLevels.INFO, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024 * 1024
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert not caplog.messages
        assert not self.out_file.getvalue()
        self.result_recorder.final_expected_files_transferred = 1
        self.result_printer(FinalTotalSubmissionsResult(1))
        assert not caplog.messages
        assert not self.out_file.getvalue()


class TestResultPrinter(BaseResultPrinterTest):
    """Test ResultPrinter."""

    def test_ctrl_c_error(self, caplog: LogCaptureFixture) -> None:
        """Test Ctrl+C error."""
        caplog.set_level(LogLevels.WARNING, "runway.core.providers.aws.s3")
        self.result_printer(CtrlCResult(Exception()))
        assert caplog.messages == ["cancelled: ctrl-c received"]

    def test_dry_run(self, caplog: LogCaptureFixture) -> None:
        """Test dry run."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        result = DryRunResult(
            transfer_type="upload", src="s3://mybucket/key", dest="./local/file"
        )
        self.result_printer(result)
        assert caplog.messages == [f"(dryrun) upload: {result.src} to {result.dest}"]

    def test_dry_run_unicode(self, caplog: LogCaptureFixture) -> None:
        """Test dry run."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        result = DryRunResult(
            transfer_type="upload", src="s3://mybucket/\u2713", dest="./local/file"
        )
        self.result_printer(result)
        assert caplog.messages == [f"(dryrun) upload: {result.src} to {result.dest}"]

    def test_error(self, caplog: LogCaptureFixture) -> None:
        """Test error."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        self.result_printer(ErrorResult(Exception("my exception")))
        assert caplog.messages == ["fatal error: my exception"]

    def test_error_unicode(self, caplog: LogCaptureFixture) -> None:
        """Test error."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        self.result_printer(ErrorResult(Exception("unicode exists \u2713")))
        assert caplog.messages == ["fatal error: unicode exists \u2713"]

    def test_error_while_progress(self, caplog: LogCaptureFixture) -> None:
        """Test error."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        mb = 1024**2
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(ErrorResult(Exception("my exception")))
        assert caplog.messages == ["fatal error: my exception"]
        assert not self.out_file.getvalue()

    def test_failure(self, caplog: LogCaptureFixture) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert caplog.messages == [f"upload failed: file to {dest} my exception"]

    def test_failure_but_no_expected_files_transferred_provided(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024**2
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) "
            "remaining (calculating...)\r"
        )
        assert caplog.messages == [f"upload failed: file to {dest} my exception"]

    def test_failure_for_delete(self, caplog: LogCaptureFixture) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=None,
            exception=Exception("my exception"),
        )

        self.result_printer(failure_result)
        assert caplog.messages == [f"delete failed: {src} my exception"]

    def test_failure_for_delete_but_no_expected_files_transferred_provided(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test failure."""
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=None,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert self.out_file.getvalue() == (
            "Completed 1 file(s) with ~0 file(s) remaining (calculating...)\r"
        )
        assert caplog.messages == [f"delete failed: {src} my exception"]

    def test_failure_for_delete_with_files_remaining(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=None,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert self.out_file.getvalue() == (
            "Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r"
        )
        assert caplog.messages == [f"delete failed: {src} my exception"]

    def test_failure_unicode(self, caplog: LogCaptureFixture) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "\u2713"
        dest = "s3://mybucket/test-key"
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert caplog.messages == [f"upload failed: {src} to {dest} my exception"]

    def test_failure_with_files_remaining(self, caplog: LogCaptureFixture) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024**2
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = 4 * mb
        self.result_recorder.bytes_transferred = mb
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_printer(failure_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~4.0 MiB (0 Bytes/s) with ~3 file(s) "
            "remaining (calculating...)\r"
        )
        assert caplog.messages == [f"upload failed: file to {dest} my exception"]

    def test_failure_with_progress(self, caplog: LogCaptureFixture) -> None:
        """Test failure."""
        caplog.set_level(LogLevels.ERROR, "runway.core.providers.aws.s3")
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        mb = 1024**2
        progress_result = self.get_progress_result()
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        failure_result = FailureResult(
            transfer_type=transfer_type,
            src=src,
            dest=dest,
            exception=Exception("my exception"),
        )
        self.result_recorder.bytes_failed_to_transfer = 3 * mb
        self.result_recorder.files_transferred += 1
        self.result_printer(failure_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
            "Completed 4.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining\r"
        )
        assert caplog.messages == [f"upload failed: file to {dest} my exception"]

    def test_final_total_does_not_print_out_newline_for_no_transfers(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test final total."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        self.result_recorder.final_expected_files_transferred = 0
        self.result_printer(FinalTotalSubmissionsResult(0))
        assert not self.out_file.getvalue()

    def test_final_total_notification_with_no_more_expected_progress(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test final total."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024**2
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) "
            "remaining (calculating...)\r"
        )
        assert caplog.messages == [f"upload: file to {dest}"]

        # Now the result recorder/printer is notified it was just
        # there will be no more queueing. Therefore it should
        # clear out remaining progress if the expected number of files
        # transferred is equal to the number of files that has completed
        # because this is the final task meaning we want to clear any progress
        # that is displayed.
        self.result_recorder.final_expected_files_transferred = 1
        self.result_printer(FinalTotalSubmissionsResult(1))
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) "
            "with ~0 file(s) remaining (calculating...)\r"
            "                                             "
            "                                    \n"
        )

    def test_get_progress_result(self) -> None:
        """Test get_progress_result."""
        mb = 1024**2
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
        )

    def test_get_progress_result_no_expected_transfer_bytes(self) -> None:
        """Test get_progress_result."""
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = 0
        self.result_recorder.expected_bytes_transferred = 0
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue() == "Completed 1 file(s) with 3 file(s) remaining\r"
        )

    def test_get_progress_result_still_calculating_totals_no_bytes(self) -> None:
        """Test get_progress_result."""
        self.result_recorder.expected_bytes_transferred = 0
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.bytes_transferred = 0
        self.result_recorder.files_transferred = 1
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r"
        )

    def test_get_progress_result_still_calculating_totals(self) -> None:
        """Test get_progress_result."""
        mb = 1024**2
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1.0 MiB/~20.0 MiB (0 Bytes/s) with ~3 file(s) "
            "remaining (calculating...)\r"
        )

    def test_get_progress_result_then_more_progress(self) -> None:
        """Test get_progress_result."""
        mb = 1024**2
        progress_result = self.get_progress_result()
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
        )
        self.result_recorder.bytes_transferred += mb
        self.result_printer(progress_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
            "Completed 2.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
        )

    def test_get_progress_result_transfer_speed_reporting(self) -> None:
        """Test get_progress_result."""
        mb = 1024**2
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_recorder.bytes_transfer_speed = 1024 * 7
        progress_result = self.get_progress_result()
        self.result_printer(progress_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1.0 MiB/20.0 MiB (7.0 KiB/s) with 3 file(s) remaining\r"
        )

    def test_init_no_error_file(self, mocker: MockerFixture) -> None:
        """Test __init__ no error_file."""
        mock_stderr = mocker.patch("sys.stderr", Mock())
        result = ResultPrinter(self.result_recorder, out_file=self.out_file)
        assert result._error_file == mock_stderr

    def test_init_no_out_file(self, mocker: MockerFixture) -> None:
        """Test __init__ no out_file."""
        mock_stdout = mocker.patch("sys.stdout", Mock())
        result = ResultPrinter(self.result_recorder, error_file=self.error_file)
        assert result._out_file == mock_stdout

    def test_success(self, caplog: LogCaptureFixture) -> None:
        """Test success."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert caplog.messages == [f"upload: file to {dest}"]

    def test_success_but_no_expected_files_transferred_provided(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test success but no expected files transferred provided."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024**2
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = mb
        self.result_recorder.bytes_transferred = mb

        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~1.0 MiB (0 Bytes/s) with ~0 file(s) "
            "remaining (calculating...)\r"
        )
        assert caplog.messages == [f"upload: file to {dest}"]

    def test_success_delete(self, caplog: LogCaptureFixture) -> None:
        """Test success for delete."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=None)
        self.result_printer(success_result)
        assert caplog.messages == [f"delete: {src}"]

    def test_success_delete_but_no_expected_files_transferred_provided(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test success delete but no expected files transferred provided."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=None)
        self.result_printer(success_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1 file(s) with ~0 file(s) remaining (calculating...)\r"
        )
        assert caplog.messages == [f"delete: {src}"]

    def test_success_delete_with_files_remaining(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test success delete with files remaining."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "delete"
        src = "s3://mybucket/test-key"
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=None)
        self.result_printer(success_result)
        assert (
            self.out_file.getvalue()
            == "Completed 1 file(s) with ~3 file(s) remaining (calculating...)\r"
        )
        assert caplog.messages == [f"delete: {src}"]

    def test_success_unicode_src(self, caplog: LogCaptureFixture) -> None:
        """Test success."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        result = SuccessResult(
            transfer_type="delete", src="s3://mybucket/tmp/\u2713", dest=None
        )
        self.result_printer(result)
        assert caplog.messages == [f"delete: {result.src}"]

    def test_success_unicode_src_and_dest(self, caplog: LogCaptureFixture) -> None:
        """Test success."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        result = SuccessResult(
            transfer_type="upload", src="/tmp/\u2713", dest="s3://mybucket/test-key"
        )
        self.result_printer(result)
        assert caplog.messages == [f"upload: {result.src} to {result.dest}"]

    def test_success_with_files_remaining(self, caplog: LogCaptureFixture) -> None:
        """Test success with files remaining."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        mb = 1024**2
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.files_transferred = 1
        self.result_recorder.expected_bytes_transferred = 4 * mb
        self.result_recorder.bytes_transferred = mb
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_printer(success_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/~4.0 MiB (0 Bytes/s) with ~3 file(s) "
            "remaining (calculating...)\r"
        )
        assert caplog.messages == [f"upload: file to {dest}"]

    def test_success_with_progress(self, caplog: LogCaptureFixture) -> None:
        """Test success with progress."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        mb = 1024**2
        progress_result = self.get_progress_result()
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)
        transfer_type = "upload"
        src = "file"
        dest = "s3://mybucket/test-key"
        success_result = SuccessResult(transfer_type=transfer_type, src=src, dest=dest)
        self.result_recorder.files_transferred += 1
        self.result_printer(success_result)
        assert self.out_file.getvalue() == (
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining\r"
        )
        assert caplog.messages == [f"upload: file to {dest}"]

    def test_unknown_result_object(self) -> None:
        """Test unknown result object."""
        self.result_printer(object())
        assert self.out_file.getvalue() == ""
        assert self.error_file.getvalue() == ""

    def test_warning(self, caplog: LogCaptureFixture) -> None:
        """Test warning."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_printer(PrintTask("warning: my warning"))
        assert caplog.messages == ["warning: my warning"]

    def test_warning_unicode(self, caplog: LogCaptureFixture) -> None:
        """Test warning."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        self.result_recorder.final_expected_files_transferred = 1
        self.result_recorder.expected_files_transferred = 1
        self.result_recorder.files_transferred = 1
        self.result_printer(PrintTask("warning: unicode exists \u2713"))
        assert caplog.messages == ["warning: unicode exists \u2713"]

    def test_warning_with_progress(self, caplog: LogCaptureFixture) -> None:
        """Test warning."""
        caplog.set_level(LogLevels.NOTICE, "runway.core.providers.aws.s3")
        shared_file = self.out_file
        self.result_printer = ResultPrinter(
            result_recorder=self.result_recorder,
            out_file=shared_file,
            error_file=shared_file,
        )
        mb = 1024**2
        progress_result = self.get_progress_result()
        self.result_recorder.expected_bytes_transferred = 20 * mb
        self.result_recorder.expected_files_transferred = 4
        self.result_recorder.final_expected_files_transferred = 4
        self.result_recorder.bytes_transferred = mb
        self.result_recorder.files_transferred = 1
        self.result_printer(progress_result)
        self.result_printer(PrintTask("warning: my warning"))
        assert shared_file.getvalue() == (
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining\r"
        )
        assert caplog.messages == ["warning: my warning"]


class TestResultProcessor:
    """Test ResultProcessor."""

    result_processor: ResultProcessor
    result_queue: "Queue[Any]"

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_queue = Queue()
        self.result_processor = ResultProcessor(self.result_queue)

    def test_run_error(self, mocker: MockerFixture) -> None:
        """Test run ErrorResult."""
        error_result = ErrorResult(Exception())
        mock_process_result = mocker.patch.object(ResultProcessor, "_process_result")
        self.result_queue.put(error_result)
        self.result_queue.put(ShutdownThreadRequest())
        assert not self.result_processor.run()
        mock_process_result.assert_called_once_with(error_result)
        assert not self.result_processor._result_handlers_enabled

    def test_process_result_handle_error(self) -> None:
        """Test _process_result."""
        mock_handler = Mock(side_effect=Exception)
        result_processor = ResultProcessor(self.result_queue, [mock_handler])
        q_result = QueuedResult(total_transfer_size=0)
        self.result_queue.put(q_result)
        self.result_queue.put(ShutdownThreadRequest())
        assert not result_processor.run()
        mock_handler.assert_called_once_with(q_result)


class TestResultRecorder:
    """Test ResultRecorder."""

    result_recorder: ResultRecorder

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.result_recorder = ResultRecorder()

    def test_get_ongoing_dict_key(self) -> None:
        """Test _get_ongoing_dict_key."""
        with pytest.raises(TypeError):
            self.result_recorder._get_ongoing_dict_key(Mock())  # type: ignore

    def test_record_error_result(self) -> None:
        """Test _record_error_result."""
        assert self.result_recorder.errors == 0
        assert not self.result_recorder(ErrorResult(exception=Exception()))
        assert self.result_recorder.errors == 1

    def test_record_final_expected_files(self) -> None:
        """Test _record_final_expected_files."""
        assert not self.result_recorder.final_expected_files_transferred
        assert not self.result_recorder(
            FinalTotalSubmissionsResult(total_submissions=13)
        )
        assert self.result_recorder.final_expected_files_transferred == 13

    def test_record_progress_result_start_time(self, mocker: MockerFixture) -> None:
        """Test _record_progress_result set start_time."""
        mock_time = mocker.patch("time.time", return_value=time.time())
        assert not self.result_recorder.start_time
        assert not self.result_recorder(
            ProgressResult(
                total_transfer_size=13, timestamp=time.time(), bytes_transferred=0
            )
        )
        assert self.result_recorder.start_time == mock_time.return_value

    def test_record_progress_result_timestamp_greater(self) -> None:
        """Test _record_progress_result timestamp greater."""
        now = time.time()
        self.result_recorder.start_time = EPOCH_TIME.timestamp()
        assert self.result_recorder.bytes_transferred == 0
        assert not self.result_recorder(
            ProgressResult(
                total_transfer_size=13,
                timestamp=now,
                bytes_transferred=1,
                transfer_type="upload",
            )
        )
        assert self.result_recorder.bytes_transfer_speed == 1 / (
            now - self.result_recorder.start_time
        )

    def test_record_progress_result_unknown_ongoing_transfer_size(self) -> None:
        """Test _record_progress_result unknown ongoing transfer size."""
        now = time.time()
        assert self.result_recorder.expected_bytes_transferred == 0
        assert not self.result_recorder(
            ProgressResult(
                total_transfer_size=None,  # type: ignore
                timestamp=now,
                bytes_transferred=1,
                transfer_type="upload",
            )
        )
        assert self.result_recorder.expected_bytes_transferred == 1
        assert not self.result_recorder(
            ProgressResult(
                total_transfer_size=None,  # type: ignore
                timestamp=now,
                bytes_transferred=1,
                transfer_type="upload",
            )
        )
        assert self.result_recorder.expected_bytes_transferred == 2


class TestUploadStreamResultSubscriber(BaseResultSubscriberTest):
    """Test UploadStreamResultSubscriber."""

    result_subscriber: UploadStreamResultSubscriber

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        super().setup_method()
        self.dest = "s3://" + self.bucket + "/" + self.key
        self.src = None  # type: ignore
        self.result_subscriber = UploadStreamResultSubscriber(self.result_queue)
        self.transfer_type = "upload"

    def test_on_queued(self) -> None:
        """Test on_queued."""
        assert not self.result_subscriber.on_queued(self.future)
        result = self.get_queued_result()
        self.assert_result_queue_is_empty()
        assert result == QueuedResult(
            transfer_type=self.transfer_type,
            src="-",
            dest=self.dest,
            total_transfer_size=self.size,
        )
