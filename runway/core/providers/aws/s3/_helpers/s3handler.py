"""S3 handler.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/s3handler.py

"""
from __future__ import annotations

import logging
import os
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from s3transfer.manager import TransferManager

from .results import (
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
    ResultPrinter,
    ResultProcessor,
    ResultRecorder,
    SuccessResult,
    Union,
    UploadResultSubscriber,
    UploadStreamResultSubscriber,
)
from .transfer_config import create_transfer_config_from_runtime_config
from .utils import (
    MAX_UPLOAD_SIZE,
    DeleteCopySourceObjectSubscriber,
    DeleteSourceFileSubscriber,
    DeleteSourceObjectSubscriber,
    DirectoryCreatorSubscriber,
    NonSeekableStream,
    ProvideCopyContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber,
    ProvideSizeSubscriber,
    ProvideUploadContentTypeSubscriber,
    RequestParamsMapper,
    StdoutBytesWriter,
    create_warning,
    find_bucket_key,
    human_readable_size,
    relative_path,
)

if TYPE_CHECKING:
    from queue import Queue

    from mypy_boto3_s3.client import S3Client
    from s3transfer.futures import TransferFuture
    from s3transfer.subscribers import BaseSubscriber

    from ......type_defs import AnyPath
    from .file_info import FileInfo
    from .parameters import ParametersDataModel
    from .results import CommandResult
    from .transfer_config import TransferConfigDict

LOGGER = logging.getLogger(__name__.replace("._", "."))


class StdinMissingError(Exception):
    """Stdin missing."""

    def __init__(self) -> None:
        """Instantiate class."""
        self.message = "stdin is required for this operation, but is not available"
        super().__init__(self.message)


class S3TransferHandlerFactory:
    """Factory for S3TransferHandlers."""

    MAX_IN_MEMORY_CHUNKS: ClassVar[int] = 6

    def __init__(
        self, config_params: ParametersDataModel, runtime_config: TransferConfigDict
    ) -> None:
        """Instantiate class.

        Args:
            config_params: The parameters provide to the CLI command.
            runtime_config: The runtime config for the CLI command
                being run.

        """
        self._config_params = config_params
        self._runtime_config = runtime_config

    def __call__(
        self, client: S3Client, result_queue: "Queue[Any]"
    ) -> S3TransferHandler:
        """Create a S3TransferHandler instance.

        Args:
            client: The client to power the S3TransferHandler.
            result_queue: The result queue to be used to process results
                for the S3TransferHandler.

        """
        transfer_config = create_transfer_config_from_runtime_config(
            self._runtime_config
        )
        transfer_config.max_in_memory_upload_chunks = self.MAX_IN_MEMORY_CHUNKS
        transfer_config.max_in_memory_download_chunks = self.MAX_IN_MEMORY_CHUNKS

        transfer_manager = TransferManager(client, transfer_config)

        LOGGER.debug(
            "Using a multipart threshold of %s and a part size of %s",
            transfer_config.multipart_threshold,
            transfer_config.multipart_chunksize,
        )
        result_recorder = ResultRecorder()
        result_processor_handlers: List[Any] = [result_recorder]
        self._add_result_printer(result_recorder, result_processor_handlers)
        result_processor = ResultProcessor(
            result_queue=result_queue, result_handlers=result_processor_handlers
        )
        command_result_recorder = CommandResultRecorder(
            result_queue=result_queue,
            result_recorder=result_recorder,
            result_processor=result_processor,
        )

        return S3TransferHandler(
            transfer_manager=transfer_manager,
            config_params=self._config_params,
            result_command_recorder=command_result_recorder,
        )

    def _add_result_printer(
        self,
        result_recorder: ResultRecorder,
        result_processor_handlers: List[
            Union[
                NoProgressResultPrinter,
                OnlyShowErrorsResultPrinter,
                ResultPrinter,
                ResultRecorder,
            ]
        ],
    ) -> None:
        if self._config_params.quiet:
            return
        if self._config_params.only_show_errors:
            result_printer = OnlyShowErrorsResultPrinter(result_recorder)
        elif self._config_params.is_stream:
            result_printer = OnlyShowErrorsResultPrinter(result_recorder)
        elif self._config_params.no_progress:
            result_printer = NoProgressResultPrinter(result_recorder)
        else:
            result_printer = ResultPrinter(result_recorder)
        result_processor_handlers.append(result_printer)


class S3TransferHandler:
    """Backend for performing S3 transfers."""

    def __init__(
        self,
        transfer_manager: TransferManager,
        config_params: ParametersDataModel,
        result_command_recorder: CommandResultRecorder,
    ) -> None:
        """Instantiate class.

        Args:
            transfer_manager: Transfer manager to use for transfers
            config_params: The parameters passed to the CLI command in the
                form of a dictionary
            result_command_recorder: The result command recorder to be
                used to get the final result of the transfer

        """
        self._transfer_manager = transfer_manager
        self._result_command_recorder = result_command_recorder

        submitter_args = (
            self._transfer_manager,
            self._result_command_recorder.result_queue,
            config_params,
        )
        self._submitters = [
            UploadStreamRequestSubmitter(*submitter_args),
            DownloadStreamRequestSubmitter(*submitter_args),
            UploadRequestSubmitter(*submitter_args),
            DownloadRequestSubmitter(*submitter_args),
            CopyRequestSubmitter(*submitter_args),
            DeleteRequestSubmitter(*submitter_args),
            LocalDeleteRequestSubmitter(*submitter_args),
        ]

    def call(self, fileinfos: Iterator[FileInfo]) -> CommandResult:
        """Process iterable of FileInfos for transfer.

        Args:
            fileinfos: Set of FileInfos to submit to underlying transfer
                request submitters to make transfer API calls to S3

        Returns:
            The result of the command that specifies the number of
            failures and warnings encountered.

        """
        with self._result_command_recorder:
            with self._transfer_manager:
                total_submissions = 0
                for fileinfo in fileinfos:
                    for submitter in self._submitters:
                        if submitter.can_submit(fileinfo):
                            if submitter.submit(fileinfo):
                                total_submissions += 1
                            break
                self._result_command_recorder.notify_total_submissions(
                    total_submissions
                )
        return self._result_command_recorder.get_command_result()


class BaseTransferRequestSubmitter:
    """Submits transfer requests to the TransferManager.

    Given a FileInfo object and provided CLI parameters, it will add the
    necessary extra arguments and subscribers in making a call to the
    TransferManager.

    """

    REQUEST_MAPPER_METHOD: ClassVar[
        Optional[Callable[[Dict[Any, Any], Dict[Any, Any]], Any]]
    ] = None
    RESULT_SUBSCRIBER_CLASS: ClassVar[Optional[Type[BaseSubscriber]]] = None

    def __init__(
        self,
        transfer_manager: TransferManager,
        result_queue: "Queue[Any]",
        config_params: ParametersDataModel,
    ):
        """Instantiate class.

        Args:
            transfer_manager: The underlying transfer manager.
            result_queue: The result queue to use.
            config_params: The associated CLI parameters passed in to the
                command as a dictionary.

        """
        self._transfer_manager = transfer_manager
        self._result_queue = result_queue
        self._config_params = config_params

    def submit(self, fileinfo: FileInfo) -> Optional[TransferFuture]:
        """Submit a transfer request based on the FileInfo provided.

        There is no guarantee that the transfer request will be made on
        behalf of the fileinfo as a fileinfo may be skipped based on
        circumstances in which the transfer is not possible.

        Args:
            fileinfo: The FileInfo to be used to submit a transfer
                request to the underlying transfer manager.

        Returns:
            A TransferFuture representing the transfer if it the
            transfer was submitted. If it was not submitted nothing
            is returned.

        """
        should_skip = self._warn_and_signal_if_skip(fileinfo)
        if not should_skip:
            return self._do_submit(fileinfo)
        return None

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        raise NotImplementedError("can_submit()")

    def _do_submit(self, fileinfo: FileInfo) -> Optional[TransferFuture]:
        """Do submit."""
        extra_args: Dict[Any, Any] = {}
        if self.REQUEST_MAPPER_METHOD:
            # pylint: disable=not-callable
            # TODO revisit in future releases of pyright - not seeing second arg
            self.REQUEST_MAPPER_METHOD(extra_args, self._config_params.dict())  # type: ignore
        subscribers: List[BaseSubscriber] = []
        self._add_additional_subscribers(subscribers, fileinfo)
        # The result subscriber class should always be the last registered
        # subscriber to ensure it is not missing any information that
        # may have been added in a different subscriber such as size.
        if self.RESULT_SUBSCRIBER_CLASS:
            result_kwargs: Dict[str, Any] = {"result_queue": self._result_queue}
            if self._config_params.is_move:
                result_kwargs["transfer_type"] = "move"
            # pylint: disable=not-callable
            subscribers.append(self.RESULT_SUBSCRIBER_CLASS(**result_kwargs))

        if not self._config_params.dryrun:
            return self._submit_transfer_request(fileinfo, extra_args, subscribers)
        return self._submit_dryrun(fileinfo)

    def _submit_dryrun(self, fileinfo: FileInfo) -> None:
        """Submit dryrun."""
        transfer_type = fileinfo.operation_name
        if self._config_params.is_move:
            transfer_type = "move"
        src, dest = self._format_src_dest(fileinfo)
        self._result_queue.put(
            DryRunResult(transfer_type=transfer_type, src=src, dest=dest)
        )

    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""

    def _submit_transfer_request(
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> TransferFuture:
        """Submit transfer request."""
        raise NotImplementedError("_submit_transfer_request()")

    def _warn_and_signal_if_skip(self, fileinfo: FileInfo) -> bool:
        """Warn and signal if skip."""
        for warning_handler in self._get_warning_handlers():
            if warning_handler(fileinfo):
                # On the first warning handler that returns a signal to skip
                # immediately propagate this signal and no longer check
                # the other warning handlers as no matter what the file will
                # be skipped.
                return True
        return False

    # pylint: disable=no-self-use
    def _get_warning_handlers(self) -> List[Callable[[FileInfo], Any]]:
        """Return a list of warning handlers, which are callables.

        Handlers take in a single parameter representing a FileInfo.
        It will then add a warning to result_queue if needed and return True if
        that FileInfo should be skipped.

        """
        return []

    def _should_inject_content_type(self) -> bool:
        """If should inject content type."""
        return bool(
            self._config_params.guess_mime_type and not self._config_params.content_type
        )

    def _warn_glacier(self, fileinfo: FileInfo) -> bool:
        """Warn glacier."""
        if not self._config_params.force_glacier_transfer:
            if not fileinfo.is_glacier_compatible:
                LOGGER.debug(
                    "Encountered glacier object s3://%s. Not performing "
                    "%s on object.",
                    fileinfo.src,
                    fileinfo.operation_name,
                )
                if not self._config_params.ignore_glacier_warnings:
                    warning = create_warning(
                        f"s3://{fileinfo.src}",
                        "Object is of storage class GLACIER. Unable to "
                        f"perform {fileinfo.operation_name} operations on GLACIER objects. "
                        "You must restore the object to be able to perform the "
                        f"operation. See aws s3 {fileinfo.operation_name} help "
                        "for additional parameter options to ignore or force these "
                        "transfers.",
                    )
                    self._result_queue.put(warning)
                return True
        return False

    def _warn_parent_reference(self, fileinfo: FileInfo) -> bool:
        """Warn parent reference."""
        # normpath() will use the OS path separator so we
        # need to take that into account when checking for a parent prefix.
        parent_prefix = ".." + os.path.sep
        escapes_cwd = (
            os.path.normpath(fileinfo.compare_key).startswith(parent_prefix)
            if fileinfo.compare_key
            else False
        )
        if escapes_cwd:
            warning = create_warning(
                fileinfo.compare_key, "File references a parent directory."
            )
            self._result_queue.put(warning)
            return True
        return False

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return formatted versions of a fileinfos source and destination."""
        raise NotImplementedError("_format_src_dest()")

    def _format_local_path(self, path: Optional[AnyPath]) -> Optional[str]:
        """Format local path."""
        return relative_path(path)

    def _format_s3_path(self, path: Optional[AnyPath]) -> Optional[str]:
        """Format s3 path."""
        if not path:
            return None
        path = str(path)
        if path.startswith("s3://"):
            return path
        return "s3://" + path


class UploadRequestSubmitter(BaseTransferRequestSubmitter):
    """Upload request submitter."""

    REQUEST_MAPPER_METHOD: ClassVar[
        Callable[[Dict[Any, Any], Dict[Any, Any]], Any]
    ] = RequestParamsMapper.map_put_object_params
    RESULT_SUBSCRIBER_CLASS: ClassVar[
        Type[UploadResultSubscriber]
    ] = UploadResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return fileinfo.operation_name == "upload"

    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        if self._should_inject_content_type():
            subscribers.append(ProvideUploadContentTypeSubscriber())
        if self._config_params.is_move:
            subscribers.append(DeleteSourceFileSubscriber())

    def _submit_transfer_request(
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> TransferFuture:
        """Submit transfer request."""
        bucket, key = find_bucket_key(str(fileinfo.dest))
        filein = self._get_filein(fileinfo)
        return self._transfer_manager.upload(
            fileobj=filein,
            bucket=bucket,
            key=key,
            extra_args=extra_args,
            subscribers=subscribers,
        )

    @staticmethod
    def _get_filein(fileinfo: FileInfo) -> str:
        """Get file in."""
        return str(fileinfo.src)

    def _get_warning_handlers(self) -> List[Callable[[FileInfo], Any]]:
        """Get warning handlers."""
        return [self._warn_if_too_large]

    def _warn_if_too_large(self, fileinfo: FileInfo) -> None:
        """Warn if too large."""
        if fileinfo.size and fileinfo.size > MAX_UPLOAD_SIZE:
            file_path = relative_path(fileinfo.src)
            warning_message = (
                f"File {file_path} exceeds s3 upload limit of "
                f"{human_readable_size(MAX_UPLOAD_SIZE)}."
            )
            warning = create_warning(file_path, warning_message, skip_file=False)
            self._result_queue.put(warning)

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return formatted versions of a fileinfos source and destination."""
        src = self._format_local_path(fileinfo.src)
        dest = self._format_s3_path(fileinfo.dest)
        return src, dest


class DownloadRequestSubmitter(BaseTransferRequestSubmitter):
    """Download request submitter."""

    REQUEST_MAPPER_METHOD: ClassVar[
        Callable[[Dict[Any, Any], Dict[Any, Any]], Any]
    ] = RequestParamsMapper.map_get_object_params
    RESULT_SUBSCRIBER_CLASS: ClassVar[
        Type[DownloadResultSubscriber]
    ] = DownloadResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return fileinfo.operation_name == "download"

    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        subscribers.append(DirectoryCreatorSubscriber())
        subscribers.append(
            ProvideLastModifiedTimeSubscriber(fileinfo.last_update, self._result_queue)
        )
        if self._config_params.is_move:
            subscribers.append(
                DeleteSourceObjectSubscriber(fileinfo.source_client)  # type: ignore
            )

    def _submit_transfer_request(
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> TransferFuture:
        """Submit transfer request."""
        bucket, key = find_bucket_key(str(fileinfo.src))
        return self._transfer_manager.download(
            fileobj=self._get_fileout(fileinfo),
            bucket=bucket,
            key=key,
            extra_args=extra_args,
            subscribers=subscribers,
        )

    @staticmethod
    def _get_fileout(fileinfo: FileInfo) -> str:
        """Get file out."""
        return str(fileinfo.dest)

    def _get_warning_handlers(self) -> List[Callable[[FileInfo], Any]]:
        """Get warning handlers."""
        return [self._warn_glacier, self._warn_parent_reference]

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return formatted versions of a fileinfos source and destination."""
        src = self._format_s3_path(fileinfo.src)
        dest = self._format_local_path(fileinfo.dest)
        return src, dest


class CopyRequestSubmitter(BaseTransferRequestSubmitter):
    """Copy request submitter."""

    REQUEST_MAPPER_METHOD: ClassVar[
        Callable[[Dict[Any, Any], Dict[Any, Any]], Any]
    ] = RequestParamsMapper.map_copy_object_params
    RESULT_SUBSCRIBER_CLASS: ClassVar[Type[CopyResultSubscriber]] = CopyResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return fileinfo.operation_name == "copy"

    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        if self._should_inject_content_type():
            subscribers.append(ProvideCopyContentTypeSubscriber())
        if self._config_params.is_move:
            subscribers.append(
                DeleteCopySourceObjectSubscriber(fileinfo.source_client)  # type: ignore
            )

    def _submit_transfer_request(
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> TransferFuture:
        """Submit transfer request."""
        bucket, key = find_bucket_key(str(fileinfo.dest))
        source_bucket, source_key = find_bucket_key(str(fileinfo.src))
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        return self._transfer_manager.copy(
            bucket=bucket,
            key=key,
            copy_source=copy_source,
            extra_args=extra_args,
            subscribers=subscribers,
            source_client=cast("S3Client", fileinfo.source_client),
        )

    def _get_warning_handlers(self) -> List[Callable[[FileInfo], Any]]:
        """Get warning handlers."""
        return [self._warn_glacier]

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return formatted versions of a fileinfos source and destination."""
        src = self._format_s3_path(fileinfo.src)
        dest = self._format_s3_path(fileinfo.dest)
        return src, dest


class UploadStreamRequestSubmitter(UploadRequestSubmitter):
    """Upload stream request submitter."""

    RESULT_SUBSCRIBER_CLASS: ClassVar[
        Type[UploadStreamResultSubscriber]
    ] = UploadStreamResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return bool(
            fileinfo.operation_name == "upload" and self._config_params.is_stream
        )

    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""
        expected_size = self._config_params.expected_size
        if expected_size is not None:
            subscribers.append(ProvideSizeSubscriber(int(expected_size)))

    @staticmethod
    def _get_filein(fileinfo: FileInfo) -> NonSeekableStream:  # type: ignore
        """Get file in."""
        if sys.stdin is None:
            raise StdinMissingError()
        return NonSeekableStream(sys.stdin.buffer)

    # pylint: disable=unused-argument
    def _format_local_path(self, path: Optional[AnyPath]) -> str:
        """Format local path."""
        return "-"


class DownloadStreamRequestSubmitter(DownloadRequestSubmitter):
    """Download stream result subscriber."""

    RESULT_SUBSCRIBER_CLASS: ClassVar[
        Type[DownloadStreamResultSubscriber]
    ] = DownloadStreamResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return bool(
            fileinfo.operation_name == "download" and self._config_params.is_stream
        )

    # pylint: disable=unused-argument
    def _add_additional_subscribers(
        self, subscribers: List[BaseSubscriber], fileinfo: FileInfo
    ) -> None:
        """Add additional subscribers."""

    @staticmethod
    def _get_fileout(fileinfo: FileInfo) -> StdoutBytesWriter:  # type: ignore
        """Get file out."""
        return StdoutBytesWriter()

    # pylint: disable=unused-argument
    def _format_local_path(self, path: Optional[AnyPath]) -> str:
        """Format local path."""
        return "-"


class DeleteRequestSubmitter(BaseTransferRequestSubmitter):
    """Delete request submitter."""

    REQUEST_MAPPER_METHOD: ClassVar[
        Callable[[Dict[Any, Any], Dict[Any, Any]], Any]
    ] = RequestParamsMapper.map_delete_object_params
    RESULT_SUBSCRIBER_CLASS: ClassVar[
        Type[DeleteResultSubscriber]
    ] = DeleteResultSubscriber

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return fileinfo.operation_name == "delete" and fileinfo.src_type == "s3"

    def _submit_transfer_request(
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> TransferFuture:
        """Submit transfer request."""
        bucket, key = find_bucket_key(str(fileinfo.src))
        return self._transfer_manager.delete(
            bucket=bucket, key=key, extra_args=extra_args, subscribers=subscribers
        )

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return formatted versions of a fileinfos source and destination."""
        return self._format_s3_path(fileinfo.src), None


class LocalDeleteRequestSubmitter(BaseTransferRequestSubmitter):
    """Local delete request submitter."""

    REQUEST_MAPPER_METHOD: ClassVar[
        Optional[Callable[[Dict[Any, Any], Dict[Any, Any]], Any]]
    ] = None
    RESULT_SUBSCRIBER_CLASS: ClassVar[Optional[Type[BaseSubscriber]]] = None

    def can_submit(self, fileinfo: FileInfo) -> bool:
        """Check whether it can submit a particular FileInfo.

        Args:
            fileinfo: The FileInfo to check if the transfer request
                submitter can handle.

        Returns:
            True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.

        """
        return fileinfo.operation_name == "delete" and fileinfo.src_type == "local"

    # pylint: disable=unused-argument
    def _submit_transfer_request(  # type: ignore
        self,
        fileinfo: FileInfo,
        extra_args: Dict[str, Any],
        subscribers: List[BaseSubscriber],
    ) -> bool:
        """Submit transfer request.

        This is quirky but essentially instead of relying on a built-in
        method of s3 transfer, the logic lives directly in the submitter.
        The reason a explicit delete local file does not
        live in s3transfer is because it is outside the scope of s3transfer;
        it should only have interfaces for interacting with S3. Therefore,
        the burden of this functionality should live in the CLI.

        The main downsides in doing this is that delete and the result
        creation happens in the main thread as opposed to a separate thread
        in s3transfer. However, this is not too big of a downside because
        deleting a local file only happens for sync --delete downloads and
        is very fast compared to all of the other types of transfers.

        """
        src, dest = self._format_src_dest(fileinfo)
        result_kwargs = {"transfer_type": "delete", "src": src, "dest": dest}
        try:
            self._result_queue.put(QueuedResult(total_transfer_size=0, **result_kwargs))
            os.remove(fileinfo.src)
            self._result_queue.put(SuccessResult(**result_kwargs))
        except Exception as exc:  # pylint: disable=broad-except
            self._result_queue.put(FailureResult(exception=exc, **result_kwargs))
        return True

    def _format_src_dest(
        self, fileinfo: FileInfo
    ) -> Tuple[Optional[str], Optional[str]]:
        return self._format_local_path(fileinfo.src), None
