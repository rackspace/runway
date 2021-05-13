"""S3 results.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/results.py

"""
from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    NamedTuple,
    Optional,
    TextIO,
    Tuple,
    Type,
    Union,
    cast,
)

from s3transfer.exceptions import CancelledError, FatalError
from typing_extensions import Literal

from ......utils import ensure_string
from .utils import (
    OnDoneFilteredSubscriber,
    PrintTask,
    human_readable_size,
    relative_path,
    uni_print,
)

if TYPE_CHECKING:
    from types import TracebackType

    from s3transfer.futures import TransferFuture

    from ......_logging import RunwayLogger
    from ......type_defs import AnyPath


LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


class CommandResult(NamedTuple):
    """Command result."""

    num_tasks_failed: int
    num_tasks_warned: int
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class CtrlCResult(NamedTuple):
    """Keyboard exit."""

    exception: Exception
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class DryRunResult(NamedTuple):
    """Dry run result."""

    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class ErrorResult(NamedTuple):
    """Error."""

    exception: BaseException
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class FailureResult(NamedTuple):
    """Failure."""

    exception: Exception
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class FinalTotalSubmissionsResult(NamedTuple):
    """Final total submissions."""

    total_submissions: int
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class ProgressResult(NamedTuple):
    """Progress."""

    bytes_transferred: int
    timestamp: float
    total_transfer_size: int
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class SuccessResult(NamedTuple):
    """Success."""

    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


class QueuedResult(NamedTuple):
    """Queued."""

    total_transfer_size: int
    dest: Optional[str] = None
    src: Optional[str] = None
    transfer_type: Optional[str] = None


AllResultTypes = (
    CommandResult,
    CtrlCResult,
    DryRunResult,
    ErrorResult,
    FailureResult,
    FinalTotalSubmissionsResult,
    ProgressResult,
    SuccessResult,
    QueuedResult,
)
AnyResult = Union[
    CommandResult,
    CtrlCResult,
    DryRunResult,
    ErrorResult,
    FailureResult,
    FinalTotalSubmissionsResult,
    ProgressResult,
    QueuedResult,
    SuccessResult,
]


class ShutdownThreadRequest:
    """Shutdown thread request."""


class BaseResultSubscriber(OnDoneFilteredSubscriber):
    """Base result subscriber."""

    TRANSFER_TYPE: ClassVar[Optional[str]] = None

    def __init__(
        self, result_queue: "queue.Queue[Any]", transfer_type: Optional[str] = None
    ):
        """Send result notifications during transfer process.

        Args:
            result_queue: The queue to place results to be processed later
                on.
            transfer_type: Type of transfer.

        """
        self._result_queue = result_queue
        self._result_kwargs_cache: Dict[str, Any] = {}
        self._transfer_type = transfer_type
        if transfer_type is None:
            self._transfer_type = self.TRANSFER_TYPE

    def on_queued(self, future: TransferFuture, **_: Any) -> None:
        """On queue."""
        self._add_to_result_kwargs_cache(future)
        result_kwargs = self._result_kwargs_cache[future.meta.transfer_id]  # type: ignore
        queued_result = QueuedResult(**result_kwargs)
        self._result_queue.put(queued_result)

    def on_progress(
        self, future: TransferFuture, bytes_transferred: int, **_: Any
    ) -> None:
        """On progress."""
        result_kwargs: Dict[str, Any] = self._result_kwargs_cache.get(
            cast(str, future.meta.transfer_id), cast(Dict[str, Any], {})
        )
        progress_result = ProgressResult(
            bytes_transferred=bytes_transferred, timestamp=time.time(), **result_kwargs
        )
        self._result_queue.put(progress_result)

    def _on_success(self, future: TransferFuture) -> None:
        """On success."""
        result_kwargs = self._on_done_pop_from_result_kwargs_cache(future)
        self._result_queue.put(SuccessResult(**result_kwargs))

    def _on_failure(self, future: TransferFuture, exception: Exception) -> None:
        """On failure."""
        result_kwargs = self._on_done_pop_from_result_kwargs_cache(future)
        if isinstance(exception, CancelledError):
            error_result_cls = CtrlCResult
            if isinstance(exception, FatalError):
                error_result_cls = ErrorResult
            self._result_queue.put(error_result_cls(exception=exception))
        else:
            self._result_queue.put(FailureResult(exception=exception, **result_kwargs))

    def _add_to_result_kwargs_cache(self, future: TransferFuture) -> None:
        """Add to results cache."""
        src, dest = self._get_src_dest(future)
        result_kwargs = {
            "transfer_type": self._transfer_type,
            "src": src,
            "dest": dest,
            "total_transfer_size": future.meta.size,
        }
        self._result_kwargs_cache[cast(str, future.meta.transfer_id)] = result_kwargs

    def _on_done_pop_from_result_kwargs_cache(
        self, future: TransferFuture
    ) -> Dict[str, Any]:
        """On done, pop from results cache."""
        result_kwargs: Dict[str, Any] = self._result_kwargs_cache.pop(
            cast(str, future.meta.transfer_id)
        )
        result_kwargs.pop("total_transfer_size")
        return result_kwargs

    def _get_src_dest(self, future: TransferFuture) -> Tuple[str, str]:
        """Get source destination."""
        raise NotImplementedError("_get_src_dest()")


class UploadResultSubscriber(BaseResultSubscriber):
    """Upload result subscriber."""

    TRANSFER_TYPE: ClassVar[Literal["upload"]] = "upload"

    def _get_src_dest(self, future: TransferFuture) -> Tuple[str, str]:
        call_args = future.meta.call_args
        src = self._get_src(call_args.fileobj)
        dest = "s3://" + call_args.bucket + "/" + call_args.key
        return src, dest

    # pylint: disable=no-self-use
    def _get_src(self, fileobj: AnyPath) -> str:
        return relative_path(fileobj)


class UploadStreamResultSubscriber(UploadResultSubscriber):
    """Upload stream result subscriber."""

    # pylint: disable=no-self-use,unused-argument
    def _get_src(self, fileobj: AnyPath) -> str:
        return "-"


class DownloadResultSubscriber(BaseResultSubscriber):
    """Download result subscriber."""

    TRANSFER_TYPE: ClassVar[Literal["download"]] = "download"

    def _get_src_dest(self, future: TransferFuture) -> Tuple[str, str]:
        call_args = future.meta.call_args
        src = "s3://" + call_args.bucket + "/" + call_args.key
        dest = self._get_dest(call_args.fileobj)
        return src, dest

    # pylint: disable=no-self-use
    def _get_dest(self, fileobj: AnyPath) -> str:
        return relative_path(fileobj)


class DownloadStreamResultSubscriber(DownloadResultSubscriber):
    """Download stream result subscriber."""

    def _get_dest(self, fileobj: AnyPath) -> str:
        return "-"


class CopyResultSubscriber(BaseResultSubscriber):
    """Copy result subscriber."""

    TRANSFER_TYPE: ClassVar[Literal["copy"]] = "copy"

    def _get_src_dest(self, future: TransferFuture) -> Tuple[str, str]:
        call_args = future.meta.call_args
        copy_source = call_args.copy_source
        src = "s3://" + copy_source["Bucket"] + "/" + copy_source["Key"]
        dest = "s3://" + call_args.bucket + "/" + call_args.key
        return src, dest


class DeleteResultSubscriber(BaseResultSubscriber):
    """Delete result subscriber."""

    TRANSFER_TYPE: ClassVar[Literal["delete"]] = "delete"

    def _get_src_dest(self, future: TransferFuture) -> Tuple[str, None]:  # type: ignore
        call_args = future.meta.call_args
        src = "s3://" + call_args.bucket + "/" + call_args.key
        return src, None


class BaseResultHandler:
    """Base handler class to be called in the ResultProcessor."""

    def __call__(self, result: Any) -> None:
        """Call instance of class."""
        raise NotImplementedError("__call__()")


class ResultRecorder(BaseResultHandler):
    """Record and track transfer statistics based on results received."""

    def __init__(self):
        """Instantiate class."""
        self.bytes_transferred = 0
        self.bytes_failed_to_transfer = 0
        self.files_transferred = 0
        self.files_failed = 0
        self.files_warned = 0
        self.errors = 0
        self.expected_bytes_transferred = 0
        self.expected_files_transferred = 0
        self.final_expected_files_transferred = None

        self.start_time = None
        self.bytes_transfer_speed = 0

        self._ongoing_progress = defaultdict(int)
        self._ongoing_total_sizes: Dict[str, int] = {}

        self._result_handler_map = {
            QueuedResult: self._record_queued_result,
            ProgressResult: self._record_progress_result,
            SuccessResult: self._record_success_result,
            FailureResult: self._record_failure_result,
            PrintTask: self._record_warning_result,
            ErrorResult: self._record_error_result,
            CtrlCResult: self._record_error_result,
            FinalTotalSubmissionsResult: self._record_final_expected_files,
        }

    def expected_totals_are_final(self) -> bool:
        """Assess if expected totals are final."""
        return self.final_expected_files_transferred == self.expected_files_transferred

    def __call__(self, result: Any) -> None:
        """Record the result of an individual Result object."""
        self._result_handler_map.get(type(result), self._record_noop)(result=result)

    @staticmethod
    def _get_ongoing_dict_key(result: Union[AnyResult, object]) -> str:
        if not isinstance(result, AllResultTypes):
            raise TypeError(
                "Any result using _get_ongoing_dict_key must be one of "
                f"{', '.join(str(i) for i in AllResultTypes)}. "
                f"Provided result is of type: {type(result)}"
            )
        key_parts: List[str] = []
        for result_property in [result.transfer_type, result.src, result.dest]:
            if result_property is not None:
                key_parts.append(ensure_string(result_property))
        return ":".join(key_parts)

    def _pop_result_from_ongoing_dicts(
        self, result: AnyResult
    ) -> Tuple[int, Optional[int]]:
        ongoing_key = self._get_ongoing_dict_key(result)
        total_progress = self._ongoing_progress.pop(ongoing_key, 0)
        total_file_size = self._ongoing_total_sizes.pop(ongoing_key, None)
        return total_progress, total_file_size

    def _record_noop(self, **_: Any) -> None:
        """If result does not have a handler, then do nothing with it."""

    def _record_queued_result(self, result: QueuedResult, **_: Any) -> None:
        if self.start_time is None:
            self.start_time = time.time()
        total_transfer_size = result.total_transfer_size
        self._ongoing_total_sizes[
            self._get_ongoing_dict_key(result)
        ] = total_transfer_size
        # The total transfer size can be None if we do not know the size
        # immediately so do not add to the total right away.
        if total_transfer_size:
            self.expected_bytes_transferred += total_transfer_size
        self.expected_files_transferred += 1

    def _record_progress_result(self, result: ProgressResult, **_: Any) -> None:
        if self.start_time is None:
            self.start_time = time.time()
        bytes_transferred = result.bytes_transferred
        self._update_ongoing_transfer_size_if_unknown(result)
        self._ongoing_progress[self._get_ongoing_dict_key(result)] += bytes_transferred
        self.bytes_transferred += bytes_transferred
        # Since the start time is captured in the result recorder and
        # capture timestamps in the subscriber, there is a chance that if
        # a progress result gets created right after the queued result
        # gets created that the timestamp on the progress result is less
        # than the timestamp of when the result processor actually
        # processes that initial queued result. So this will avoid
        # negative progress being displayed or zero division occuring.
        if result.timestamp > self.start_time:
            self.bytes_transfer_speed = self.bytes_transferred / (
                result.timestamp - self.start_time
            )

    def _update_ongoing_transfer_size_if_unknown(self, result: ProgressResult) -> None:
        """Handle transfer size unknown but shown in progress result."""
        ongoing_key = self._get_ongoing_dict_key(result)
        if self._ongoing_total_sizes.get(ongoing_key) is None:
            total_transfer_size = result.total_transfer_size
            # If the total size is no longer None that means we just learned
            # of the size so let's update the appropriate places with this
            # knowledge
            if result.total_transfer_size is not None:
                self._ongoing_total_sizes[ongoing_key] = total_transfer_size
                # Figure out how many bytes have been unaccounted for as
                # the recorder has been keeping track of how many bytes
                # it has seen so far and add it to the total expected amount.
                ongoing_progress = self._ongoing_progress[ongoing_key]
                unaccounted_bytes = total_transfer_size - ongoing_progress
                self.expected_bytes_transferred += unaccounted_bytes
            # If we still do not know what the total transfer size is
            # just update the expected bytes with the know bytes transferred
            # as we know at the very least, those bytes are expected.
            else:
                self.expected_bytes_transferred += result.bytes_transferred

    def _record_success_result(self, result: AnyResult, **_: Any) -> None:
        self._pop_result_from_ongoing_dicts(result)
        self.files_transferred += 1

    def _record_failure_result(self, result: AnyResult, **_: Any) -> None:
        """On failure, account for the failure in count for bytes transferred."""
        total_progress, total_file_size = self._pop_result_from_ongoing_dicts(result)
        if total_file_size is not None:
            progress_left = total_file_size - total_progress
            self.bytes_failed_to_transfer += progress_left

        self.files_failed += 1
        self.files_transferred += 1

    def _record_warning_result(self, **_: Any) -> None:
        self.files_warned += 1

    def _record_error_result(self, **_: Any) -> None:
        self.errors += 1

    def _record_final_expected_files(
        self, result: FinalTotalSubmissionsResult, **_: Any
    ) -> None:
        self.final_expected_files_transferred = result.total_submissions


class ResultPrinter(BaseResultHandler):
    """Prints status of ongoing transfer."""

    _FILES_REMAINING: ClassVar[str] = "{remaining_files} file(s) remaining"
    _ESTIMATED_EXPECTED_TOTAL: ClassVar[str] = "~{expected_total}"
    _STILL_CALCULATING_TOTALS: ClassVar[str] = " (calculating...)"
    BYTE_PROGRESS_FORMAT: ClassVar[str] = (
        "Completed {bytes_completed}/{expected_bytes_completed} "
        "({transfer_speed}) with " + _FILES_REMAINING
    )
    FILE_PROGRESS_FORMAT: ClassVar[str] = (
        "Completed {files_completed} file(s) with " + _FILES_REMAINING
    )
    SUCCESS_FORMAT: ClassVar[str] = "{transfer_type}: {transfer_location}"
    DRY_RUN_FORMAT: ClassVar[str] = "(dryrun) " + SUCCESS_FORMAT
    FAILURE_FORMAT: ClassVar[
        str
    ] = "{transfer_type} failed: {transfer_location} {exception}"
    WARNING_FORMAT: ClassVar[str] = "{message}"
    ERROR_FORMAT: ClassVar[str] = "fatal error: {exception}"
    CTRL_C_MSG: ClassVar[str] = "cancelled: ctrl-c received"

    SRC_DEST_TRANSFER_LOCATION_FORMAT: ClassVar[str] = "{src} to {dest}"
    SRC_TRANSFER_LOCATION_FORMAT: ClassVar[str] = "{src}"

    def __init__(
        self,
        result_recorder: ResultRecorder,
        *,
        out_file: Optional[TextIO] = None,
        error_file: Optional[TextIO] = None,
    ):
        """Instantiate class.

        Args:
            result_recorder: The associated result recorder
            out_file: Location to write progress and success statements.
                By default, the location is sys.stdout.
            error_file: Location to write warnings and errors.
                By default, the location is sys.stderr.

        """
        self._result_recorder = result_recorder
        self._out_file = out_file
        if self._out_file is None:
            self._out_file = sys.stdout
        self._error_file = error_file
        if self._error_file is None:
            self._error_file = sys.stderr
        self._progress_length = 0
        self._result_handler_map = {
            ProgressResult: self._print_progress,
            SuccessResult: self._print_success,
            FailureResult: self._print_failure,
            PrintTask: self._print_warning,
            ErrorResult: self._print_error,
            CtrlCResult: self._print_ctrl_c,
            DryRunResult: self._print_dry_run,
            FinalTotalSubmissionsResult: self._clear_progress_if_no_more_expected_transfers,
        }

    def __call__(self, result: Any) -> None:
        """Print the progress of the ongoing transfer based on a result."""
        self._result_handler_map.get(type(result), self._print_noop)(result=result)

    def _print_noop(self, **_: Any) -> None:
        """If result does not have a handler, then do nothing with it."""

    def _print_dry_run(self, result: DryRunResult, **_: Any) -> None:
        statement = self.DRY_RUN_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result),
        )
        LOGGER.notice(statement)

    def _print_success(self, result: SuccessResult, **_: Any) -> None:
        success_statement = self.SUCCESS_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result),
        )
        LOGGER.notice(success_statement)
        self._redisplay_progress()

    def _print_failure(self, result: FailureResult, **_: Any) -> None:
        failure_statement = self.FAILURE_FORMAT.format(
            transfer_type=result.transfer_type,
            transfer_location=self._get_transfer_location(result),
            exception=result.exception,
        )
        LOGGER.error(failure_statement)
        self._redisplay_progress()

    def _print_warning(self, result: Any, **_: Any) -> None:
        warning_statement = self.WARNING_FORMAT.format(message=result.message)
        LOGGER.warning(warning_statement)
        self._redisplay_progress()

    def _print_error(self, result: ErrorResult, **_: Any) -> None:
        # pylint: disable=logging-format-interpolation
        LOGGER.error(self.ERROR_FORMAT.format(exception=result.exception))

    # pylint: disable=unused-argument
    def _print_ctrl_c(self, result: CtrlCResult, **_: Any) -> None:
        LOGGER.warning(self.CTRL_C_MSG)

    def _get_transfer_location(self, result: AnyResult) -> str:
        if result.dest is None:
            return self.SRC_TRANSFER_LOCATION_FORMAT.format(src=result.src)
        return self.SRC_DEST_TRANSFER_LOCATION_FORMAT.format(
            src=result.src, dest=result.dest
        )

    def _redisplay_progress(self) -> None:
        # Reset to zero because done statements are printed with new lines
        # meaning there are no carriage returns to take into account when
        # printing the next line.
        self._progress_length = 0
        self._add_progress_if_needed()

    def _add_progress_if_needed(self) -> None:
        if self._has_remaining_progress():
            self._print_progress()

    def _print_progress(self, **_: Any) -> None:
        # Get all of the statistics in the correct form.
        remaining_files = self._get_expected_total(
            str(
                self._result_recorder.expected_files_transferred
                - self._result_recorder.files_transferred
            )
        )

        # Create the display statement.
        if self._result_recorder.expected_bytes_transferred > 0:
            bytes_completed = human_readable_size(
                self._result_recorder.bytes_transferred
                + self._result_recorder.bytes_failed_to_transfer
            )
            expected_bytes_completed = self._get_expected_total(
                human_readable_size(self._result_recorder.expected_bytes_transferred)
            )

            transfer_speed = (
                human_readable_size(self._result_recorder.bytes_transfer_speed)
                or "0 Bytes"
            ) + "/s"
            progress_statement = self.BYTE_PROGRESS_FORMAT.format(
                bytes_completed=bytes_completed,
                expected_bytes_completed=expected_bytes_completed,
                transfer_speed=transfer_speed,
                remaining_files=remaining_files,
            )
        else:
            # We're not expecting any bytes to be transferred, so we should
            # only print of information about number of files transferred.
            progress_statement = self.FILE_PROGRESS_FORMAT.format(
                files_completed=self._result_recorder.files_transferred,
                remaining_files=remaining_files,
            )

        if not self._result_recorder.expected_totals_are_final():
            progress_statement += self._STILL_CALCULATING_TOTALS

        # Make sure that it overrides any previous progress bar.
        progress_statement = self._adjust_statement_padding(
            progress_statement, ending_char="\r"
        )
        # We do not want to include the carriage return in this calculation
        # as progress length is used for determining whitespace padding.
        # So we subtract one off of the length.
        self._progress_length = len(progress_statement) - 1

        # Print the progress out.
        self._print_to_out_file(progress_statement)

    def _get_expected_total(self, expected_total: Optional[str]) -> Optional[str]:
        if not self._result_recorder.expected_totals_are_final():
            return self._ESTIMATED_EXPECTED_TOTAL.format(expected_total=expected_total)
        return expected_total

    def _adjust_statement_padding(
        self, print_statement: str, ending_char: str = "\n"
    ) -> str:
        print_statement = print_statement.ljust(self._progress_length, " ")
        return print_statement + ending_char

    def _has_remaining_progress(self) -> bool:
        if not self._result_recorder.expected_totals_are_final():
            return True
        actual = self._result_recorder.files_transferred
        expected = self._result_recorder.expected_files_transferred
        return actual != expected

    def _print_to_out_file(self, statement: str) -> None:
        uni_print(statement, self._out_file)

    def _clear_progress_if_no_more_expected_transfers(self, **_: Any) -> None:
        if self._progress_length and not self._has_remaining_progress():
            uni_print(self._adjust_statement_padding(""), self._out_file)


class NoProgressResultPrinter(ResultPrinter):
    """A result printer that doesn't print progress."""

    def _print_progress(self, **_: Any) -> None:
        pass


class OnlyShowErrorsResultPrinter(ResultPrinter):
    """A result printer that only prints out errors."""

    def _print_progress(self, **_: Any) -> None:
        pass

    def _print_success(self, result: Any, **_: Any) -> None:
        pass


class ResultProcessor(threading.Thread):
    """Thread to process results from result queue.

    This includes recording statistics and printing transfer status

    """

    def __init__(
        self,
        result_queue: "queue.Queue[Any]",
        result_handlers: Optional[List[Callable[..., Any]]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            result_queue: The result queue to process results from
            result_handlers: A list of callables that take a result in as
                a parameter to process the result for that handler.

        """
        threading.Thread.__init__(self)
        self._result_queue = result_queue
        self._result_handlers = result_handlers or []
        self._result_handlers_enabled = True

    def run(self) -> None:
        """Run."""
        while True:
            try:
                result = self._result_queue.get(True)
                if isinstance(result, ShutdownThreadRequest):
                    LOGGER.debug(
                        "Shutdown request received in result processing "
                        "thread, shutting down result thread."
                    )
                    break
                if self._result_handlers_enabled:
                    self._process_result(result)
                # ErrorResults are fatal to the command. If a fatal error
                # is seen, we know that the command is trying to shutdown
                # so disable all of the handlers and quickly consume all
                # of the results in the result queue in order to get to
                # the shutdown request to clean up the process.
                if isinstance(result, ErrorResult):
                    self._result_handlers_enabled = False
            except queue.Empty:  # cov: ignore
                pass

    def _process_result(self, result: AnyResult) -> None:
        for result_handler in self._result_handlers:
            try:
                result_handler(result)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.debug(
                    "Error processing result %s with handler %s: %s",
                    result,
                    result_handler,
                    exc,
                    exc_info=True,
                )


class CommandResultRecorder:
    """Records the result for an entire command.

    It will fully process all results in a result queue and determine
    a CommandResult representing the entire command.

    """

    def __init__(
        self,
        result_queue: "queue.Queue[Any]",
        result_recorder: ResultRecorder,
        result_processor: ResultProcessor,
    ) -> None:
        """Instantiate class.

        Args:
            result_queue: The result queue in which results are placed on
                and processed from.
            result_recorder: The result recorder to track the various
                results sent through the result queue
            result_processor: The result processor to process results
                placed on the queue

        """
        self.result_queue = result_queue
        self._result_recorder = result_recorder
        self._result_processor = result_processor

    def start(self) -> None:
        """Start."""
        self._result_processor.start()

    def shutdown(self) -> None:
        """Shutdown."""
        self.result_queue.put(ShutdownThreadRequest())
        self._result_processor.join()

    def get_command_result(self) -> CommandResult:
        """Get the CommandResult representing the result of a command."""
        return CommandResult(
            num_tasks_failed=self._result_recorder.files_failed
            + self._result_recorder.errors,
            num_tasks_warned=self._result_recorder.files_warned,
        )

    def notify_total_submissions(self, total: int) -> None:
        """Notify total submissions."""
        self.result_queue.put(FinalTotalSubmissionsResult(total_submissions=total))

    def __enter__(self) -> CommandResultRecorder:
        """Enter the context manager.

        Returns:
            Instance of the context manager.

        """
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit the context manager."""
        if exc_type:
            LOGGER.debug(
                "Exception caught during command execution: %s",
                exc_value,
                exc_info=True,
            )
            if exc_value:
                self.result_queue.put(ErrorResult(exception=exc_value))
            self.shutdown()
            return True  # suppress error as it has been handled by the context manager
        self.shutdown()
        return None
