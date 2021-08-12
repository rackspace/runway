"""Utilities.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/utils.py
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/utils.py

"""
from __future__ import annotations

import errno
import logging
import mimetypes
import os
import os.path
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    NamedTuple,
    Optional,
    TextIO,
    Tuple,
    Union,
    overload,
)

from dateutil.parser import parse
from dateutil.tz import tzlocal, tzutc
from s3transfer.subscribers import BaseSubscriber

if TYPE_CHECKING:
    from queue import Queue

    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import ObjectTypeDef
    from s3transfer.futures import TransferFuture
    from s3transfer.utils import CallArgs

    from ......type_defs import AnyPath
    from .format_path import FormatPathResult

LOGGER = logging.getLogger(__name__.replace("._", "."))

EPOCH_TIME = datetime(1970, 1, 1, tzinfo=tzutc())
HUMANIZE_SUFFIXES = ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB")
# Maximum object size allowed in S3.
# See: http://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html
MAX_UPLOAD_SIZE = 5 * (1024 ** 4)
SIZE_SUFFIX = {
    "kb": 1024,
    "mb": 1024 ** 2,
    "gb": 1024 ** 3,
    "tb": 1024 ** 4,
    "kib": 1024,
    "mib": 1024 ** 2,
    "gib": 1024 ** 3,
    "tib": 1024 ** 4,
}

_S3_ACCESSPOINT_TO_BUCKET_KEY_REGEX = re.compile(
    r"^(?P<bucket>arn:(aws).*:s3:[a-z\-0-9]+:[0-9]{12}:accesspoint[:/][^/]+)/?"
    r"(?P<key>.*)$"
)
_S3_OUTPOST_TO_BUCKET_KEY_REGEX = re.compile(
    r"^(?P<bucket>arn:(aws).*:s3-outposts:[a-z\-0-9]+:[0-9]{12}:outpost[/:]"
    r"[a-zA-Z0-9\-]{1,63}[/:]accesspoint[/:][a-zA-Z0-9\-]{1,63})[/:]?(?P<key>.*)$"
)
_S3_OBJECT_LAMBDA_TO_BUCKET_KEY_REGEX = re.compile(
    r"^(?P<bucket>arn:(aws).*:s3-object-lambda:[a-z\-0-9]+:[0-9]{12}:"
    r"accesspoint[/:][a-zA-Z0-9\-]{1,63})[/:]?(?P<key>.*)$"
)


class BaseProvideContentTypeSubscriber(BaseSubscriber):
    """A subscriber that provides content type when creating s3 objects."""

    def on_queued(self, future: TransferFuture, **_: Any) -> None:
        """On queued."""
        guessed_type = guess_content_type(self._get_filename(future))
        if guessed_type is not None:
            future.meta.call_args.extra_args["ContentType"] = guessed_type

    def _get_filename(self, future: TransferFuture) -> str:
        raise NotImplementedError("_get_filename()")


def _date_parser(date_string: Union[datetime, str]) -> datetime:
    """Parse date string into a datetime object."""
    if isinstance(date_string, datetime):
        return date_string
    return parse(date_string).astimezone(tzlocal())


class BucketLister:
    """List keys in a bucket."""

    def __init__(
        self,
        client: S3Client,
        date_parser: Callable[[Union[datetime, str]], datetime] = _date_parser,
    ) -> None:
        """Instantiate class.

        Args:
            client: boto3 S3 client.
            date_parser: Parser for date string.

        """
        self._client = client
        self._date_parser = date_parser

    def list_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        page_size: Optional[int] = None,
        extra_args: Any = None,
    ) -> Generator[Tuple[str, ObjectTypeDef], None, None]:
        """List objects in S3 bucket.

        Args:
            bucket: Bucket name.
            prefix: Object prefix.
            page_size: Number of items per page
            extra_args: Additional arguments to pass to list call.

        """
        kwargs = {"Bucket": bucket, "PaginationConfig": {"PageSize": page_size}}
        if prefix is not None:
            kwargs["Prefix"] = prefix
        if extra_args is not None:
            kwargs.update(extra_args)

        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(**kwargs)  # type: ignore
        for page in pages:
            contents = page.get("Contents", [])
            for content in contents:
                source_path = bucket + "/" + content.get("Key", "")
                if "LastModified" in content:
                    content["LastModified"] = self._date_parser(content["LastModified"])
                yield source_path, content


class OnDoneFilteredSubscriber(BaseSubscriber):
    """Subscriber that differentiates between successes and failures.

    It is really a convenience class so developers do not have to have
    to constantly remember to have a general try/except around future.result()

    """

    def on_done(self, future: TransferFuture, **_: Any) -> None:
        """On done."""
        try:
            future.result()
        except Exception as exc:  # pylint: disable=broad-except
            self._on_failure(future, exc)
        else:
            self._on_success(future)

    def _on_success(self, future: TransferFuture) -> None:
        """On success."""

    # pylint: disable=invalid-name
    def _on_failure(self, future: TransferFuture, exception: Exception) -> None:
        """On failure."""


class DeleteSourceSubscriber(OnDoneFilteredSubscriber):
    """A subscriber which deletes the source of the transfer."""

    def _on_success(self, future: TransferFuture) -> None:
        try:
            self._delete_source(future)
        except Exception as exc:  # pylint: disable=broad-except
            future.set_exception(exc)

    # pylint: disable=no-self-use
    def _delete_source(self, future: TransferFuture) -> None:
        raise NotImplementedError("_delete_source()")


class DeleteSourceFileSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes a file."""

    def _delete_source(self, future: TransferFuture) -> None:
        os.remove(future.meta.call_args.fileobj)


class DeleteSourceObjectSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes an object."""

    def __init__(self, client: S3Client):
        """Instantiate class."""
        self._client = client

    @staticmethod
    def _get_bucket(call_args: CallArgs) -> str:
        """Get bucket."""
        return call_args.bucket

    @staticmethod
    def _get_key(call_args: CallArgs) -> str:
        """Get key."""
        return call_args.key

    def _delete_source(self, future: TransferFuture) -> None:
        """Delete source."""
        call_args = future.meta.call_args
        delete_object_kwargs = {
            "Bucket": self._get_bucket(call_args),
            "Key": self._get_key(call_args),
        }
        if call_args.extra_args.get("RequestPayer"):
            delete_object_kwargs["RequestPayer"] = call_args.extra_args["RequestPayer"]
        self._client.delete_object(**delete_object_kwargs)


class DeleteCopySourceObjectSubscriber(DeleteSourceObjectSubscriber):
    """A subscriber which deletes the copy source."""

    @staticmethod
    def _get_bucket(call_args: CallArgs) -> str:
        return call_args.copy_source["Bucket"]

    @staticmethod
    def _get_key(call_args: CallArgs) -> str:
        return call_args.copy_source["Key"]


class CreateDirectoryError(Exception):
    """Create directory error."""


class DirectoryCreatorSubscriber(BaseSubscriber):
    """Creates a directory to download if it does not exist."""

    def on_queued(self, future: TransferFuture, **_: Any):
        """On queued."""
        dirname = os.path.dirname(str(future.meta.call_args.fileobj))
        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        except OSError as exc:  # pylint: disable=broad-except
            if exc.errno != errno.EEXIST:
                raise CreateDirectoryError(
                    f"Could not create directory {dirname}: {exc}"
                ) from exc


class NonSeekableStream:
    """Wrap a file like object as a non seekable stream.

    This class is used to wrap an existing file like object
    such that it only has a ``.read()`` method.

    There are some file like objects that aren't truly seekable
    but appear to be.  For example, on windows, sys.stdin has
    a ``seek()`` method, and calling ``seek(0)`` even appears
    to work.  However, subsequent ``.read()`` calls will just
    return an empty string.

    Consumers of these file like object have no way of knowing
    if these files are truly seekable or not, so this class
    can be used to force non-seekable behavior when you know
    for certain that a fileobj is non seekable.

    """

    def __init__(self, fileobj: BinaryIO):
        """Instantiate class."""
        self._fileobj = fileobj

    def read(self, amt: Optional[int] = None) -> bytes:
        """Read."""
        if amt is None:
            return self._fileobj.read()
        return self._fileobj.read(amt)


class PrintTask(NamedTuple):
    """Print task.

    Attributes:
        message: An arbitrary string associated with the entry. This can be used
            to communicate the result of the task.
        error: Boolean indicating a failure.
        total_parts: The total number of parts for multipart transfers.
        warning: Boolean indicating a warning.

    """

    message: str
    error: bool = False
    total_parts: Optional[int] = None
    warning: bool = False


class ProvideCopyContentTypeSubscriber(BaseProvideContentTypeSubscriber):
    """Provide copy content type subscriber."""

    # pylint: disable=no-self-use
    def _get_filename(self, future: TransferFuture) -> str:
        return future.meta.call_args.copy_source["Key"]


class ProvideLastModifiedTimeSubscriber(OnDoneFilteredSubscriber):
    """Sets utime for a downloaded file."""

    def __init__(
        self, last_modified_time: datetime, result_queue: "Queue[Any]"
    ) -> None:
        """Instantiate class."""
        self._last_modified_time = last_modified_time
        self._result_queue = result_queue

    def _on_success(self, future: TransferFuture, **_: Any) -> None:
        filename = future.meta.call_args.fileobj
        try:
            last_update_tuple = self._last_modified_time.timetuple()
            mod_timestamp = time.mktime(last_update_tuple)
            set_file_utime(filename, int(mod_timestamp))
        except Exception as exc:  # pylint: disable=broad-except
            warning_message = (
                f"Successfully Downloaded {filename} but was unable to update the "
                f"last modified time. {exc}"
            )
            self._result_queue.put(create_warning(filename, warning_message))


class ProvideSizeSubscriber(BaseSubscriber):
    """A subscriber which provides the transfer size before it's queued."""

    def __init__(self, size: Optional[int]):
        """Instantiate class."""
        self.size = size or 0

    def on_queued(self, future: TransferFuture, **_: Any) -> None:
        """On Queued."""
        future.meta.provide_transfer_size(self.size)


class ProvideUploadContentTypeSubscriber(BaseProvideContentTypeSubscriber):
    """Provider upload content type subscriber."""

    # pylint: disable=no-self-use
    def _get_filename(self, future: TransferFuture) -> str:
        return str(future.meta.call_args.fileobj)


class RequestParamsMapper:
    """Utility class that maps config params to request params.

    Each method in the class maps to a particular operation and will set
    the request parameters depending on the operation and config parameters
    provided.

    For example, take the mapping of request parameters for PutObject::

        >>> cli_request_params = {'sse': 'AES256', 'storage_class': 'GLACIER'}
        >>> request_params = {}
        >>> RequestParamsMapper.map_put_object_params(
                request_params, cli_request_params)
        >>> print(request_params)
        {'StorageClass': 'GLACIER', 'ServerSideEncryption': 'AES256'}

    Note that existing parameters in ``request_params`` will be overridden if
    a parameter in ``config_params`` maps to the existing parameter.

    """

    @classmethod
    def map_copy_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to CopyObject request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_general_object_params(request_params, config_params)
        cls._set_metadata_directive_param(request_params, config_params)
        cls._set_metadata_params(request_params, config_params)
        cls._auto_populate_metadata_directive(request_params)
        cls._set_sse_request_params(request_params, config_params)
        cls._set_sse_c_and_copy_source_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_create_multipart_upload_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to CreateMultipartUpload request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_general_object_params(request_params, config_params)
        cls._set_sse_request_params(request_params, config_params)
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_metadata_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_delete_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to DeleteObject request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_get_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to GetObject request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_head_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to HeadObject request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_list_objects_v2_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to DeleteObjectV2 request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_put_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to PutObject request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_general_object_params(request_params, config_params)
        cls._set_metadata_params(request_params, config_params)
        cls._set_sse_request_params(request_params, config_params)
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_upload_part_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to UploadPart request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def map_upload_part_copy_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Map config params to UploadPartCopy request params.

        Args:
            request_params: A dictionary to be filled out with the appropriate
                parameters for the specified client operation using the current
                config parameters.
            config_params: A dictionary of the current config params that will be
                used to generate the request parameters for the specified operation.

        """
        cls._set_sse_c_and_copy_source_request_params(request_params, config_params)
        cls._set_request_payer_param(request_params, config_params)

    @classmethod
    def _auto_populate_metadata_directive(cls, request_params: Dict[Any, Any]) -> None:
        """Auto populate metadata directive."""
        if request_params.get("Metadata") and not request_params.get(
            "MetadataDirective"
        ):
            request_params["MetadataDirective"] = "REPLACE"

    @classmethod
    def _permission_to_param(cls, permission: str) -> str:
        """Permission to param."""
        if permission == "read":
            return "GrantRead"
        if permission == "full":
            return "GrantFullControl"
        if permission == "readacl":
            return "GrantReadACP"
        if permission == "writeacl":
            return "GrantWriteACP"
        raise ValueError("permission must be one of: read|readacl|writeacl|full")

    @classmethod
    def _set_general_object_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ):
        """Set general object params.

        Parameters set in this method should be applicable to the following
        operations involving objects: PutObject, CopyObject, and
        CreateMultipartUpload.

        """
        general_param_translation = {
            "acl": "ACL",
            "storage_class": "StorageClass",
            "website_redirect": "WebsiteRedirectLocation",
            "content_type": "ContentType",
            "cache_control": "CacheControl",
            "content_disposition": "ContentDisposition",
            "content_encoding": "ContentEncoding",
            "content_language": "ContentLanguage",
            "expires": "Expires",
        }
        for cli_param_name, cli_param_value in general_param_translation.items():
            if config_params.get(cli_param_name):
                request_param_name = cli_param_value
                request_params[request_param_name] = config_params[cli_param_name]
        cls._set_grant_params(request_params, config_params)

    @classmethod
    def _set_grant_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Set grant params."""
        if config_params.get("grants"):
            for grant in config_params["grants"]:
                try:
                    permission, grantee = grant.split("=", 1)
                except ValueError:
                    raise ValueError(
                        "grants should be of the form permission=principal"
                    ) from None
                request_params[cls._permission_to_param(permission)] = grantee

    @classmethod
    def _set_metadata_directive_param(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Set metadata directive param."""
        if config_params.get("metadata_directive"):
            request_params["MetadataDirective"] = config_params["metadata_directive"]

    @classmethod
    def _set_metadata_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Get metadata params."""
        if config_params.get("metadata"):
            request_params["Metadata"] = config_params["metadata"]

    @classmethod
    def _set_request_payer_param(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ):
        """Set request payer param."""
        if config_params.get("request_payer"):
            request_params["RequestPayer"] = config_params["request_payer"]

    @classmethod
    def _set_sse_c_and_copy_source_request_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Set SSE-C and copy source request params."""
        cls._set_sse_c_request_params(request_params, config_params)
        cls._set_sse_c_copy_source_request_params(request_params, config_params)

    @classmethod
    def _set_sse_c_copy_source_request_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        if config_params.get("sse_c_copy_source"):
            request_params["CopySourceSSECustomerAlgorithm"] = config_params[
                "sse_c_copy_source"
            ]
            request_params["CopySourceSSECustomerKey"] = config_params[
                "sse_c_copy_source_key"
            ]

    @classmethod
    def _set_sse_c_request_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Set SSE-C request params."""
        if config_params.get("sse_c"):
            request_params["SSECustomerAlgorithm"] = config_params["sse_c"]
            request_params["SSECustomerKey"] = config_params["sse_c_key"]

    @classmethod
    def _set_sse_request_params(
        cls, request_params: Dict[Any, Any], config_params: Dict[Any, Any]
    ) -> None:
        """Set SSE request params."""
        if config_params.get("sse"):
            request_params["ServerSideEncryption"] = config_params["sse"]
        if config_params.get("sse_kms_key_id"):
            request_params["SSEKMSKeyId"] = config_params["sse_kms_key_id"]


class StdoutBytesWriter:
    """Acts as a file-like object that performs the bytes_print function on write."""

    def __init__(self, stdout: Optional[TextIO] = None) -> None:
        """Instantiate class."""
        self._stdout = stdout

    def write(self, b: bytes) -> None:
        """Write data to stdout as bytes."""
        if self._stdout is None:
            self._stdout = sys.stdout

        if getattr(self._stdout, "buffer", None):
            self._stdout.buffer.write(b)
        else:
            # If it is not possible to write to the standard out buffer.
            # The next best option is to decode and write to standard out.
            self._stdout.write(b.decode("utf-8"))


def block_s3_object_lambda(s3_path: str) -> None:
    """Check for S3 Object Lambda resource."""
    match = _S3_OBJECT_LAMBDA_TO_BUCKET_KEY_REGEX.match(s3_path)
    if match:
        raise ValueError("S3 action does not support S3 Object Lambda resources")


def create_warning(
    path: Optional[AnyPath], error_message: str, skip_file: bool = True
) -> PrintTask:
    """Create a ``PrintTask`` for whenever a warning is to be thrown."""
    print_string = "warning: "
    if skip_file:
        print_string = f"{print_string}skipping file {path}; "
    print_string += error_message
    return PrintTask(message=print_string, error=False, warning=True)


def find_bucket_key(s3_path: str) -> Tuple[str, str]:
    """Given an S3 path return the bucket and the key represented by the S3 path.

    Args:
        s3_path: Path to an object in S3 or object prefix.

    """
    block_s3_object_lambda(s3_path)
    match = _S3_ACCESSPOINT_TO_BUCKET_KEY_REGEX.match(s3_path)
    if match:
        return match.group("bucket"), match.group("key")
    match = _S3_OUTPOST_TO_BUCKET_KEY_REGEX.match(s3_path)
    if match:
        return match.group("bucket"), match.group("key")
    s3_components = s3_path.split("/", 1)
    bucket = s3_components[0]
    s3_key = ""
    if len(s3_components) > 1:
        s3_key = s3_components[1]
    return bucket, s3_key


def find_dest_path_comp_key(
    files: FormatPathResult, src_path: Optional[AnyPath] = None
) -> Tuple[str, str]:
    """Determine destination path and compare key.

    Args:
        files: Object returned from ``FormatPath``.
        src_path: Source path.

    """
    src = files["src"]
    dest = files["dest"]
    src_type = src["type"]
    dest_type = dest["type"]
    if src_path is None:
        src_path = src["path"]
    if isinstance(src_path, Path):  # convert path to absolute path str
        if src_path.is_dir():
            src_path = f"{src_path.resolve()}{os.sep}"
        else:
            src_path = str(src_path.resolve())

    sep_table = {"s3": "/", "local": os.sep}

    if files["dir_op"]:
        rel_path = src_path[len(src["path"]) :]
    else:
        rel_path = src_path.split(sep_table[src_type])[-1]
    compare_key = rel_path.replace(sep_table[src_type], "/")
    if files["use_src_name"]:
        dest_path = dest["path"]
        dest_path += rel_path.replace(sep_table[src_type], sep_table[dest_type])
    else:
        dest_path = dest["path"]
    return dest_path, compare_key


def get_file_stat(path: Path) -> Tuple[int, Optional[datetime]]:
    """Get size of file in bytes and last modified time stamp."""
    try:
        stats = path.stat()
    except IOError as exc:
        raise ValueError(f"Could not retrieve file stat of {path}: {exc}") from exc

    try:
        update_time = datetime.fromtimestamp(stats.st_mtime, tzlocal())
    except (ValueError, OSError, OverflowError):
        update_time = None

    return stats.st_size, update_time


def guess_content_type(filename: AnyPath) -> Optional[str]:
    """Given a filename, guess it's content type.

    If the type cannot be guessed, a value of None is returned.

    """
    try:
        return mimetypes.guess_type(str(filename))[0]
    except UnicodeDecodeError:
        LOGGER.debug(
            "Unable to guess content type for %s due to " "UnicodeDecodeError: ",
            filename,
            exc_info=True,
        )
    return None


def human_readable_size(value: float) -> Optional[str]:
    """Convert a size in bytes into a human readable format.

    For example::

        >>> human_readable_size(1)
        '1 Byte'
        >>> human_readable_size(10)
        '10 Bytes'
        >>> human_readable_size(1024)
        '1.0 KiB'
        >>> human_readable_size(1024 * 1024)
        '1.0 MiB'

    Args:
        value: The size in bytes.

    Return:
        The size in a human readable format based on base-2 units.

    """
    base = 1024
    bytes_int = float(value)

    if bytes_int == 1:
        return "1 Byte"
    if bytes_int < base:
        return f"{bytes_int:.0f} Bytes"

    for i, suffix in enumerate(HUMANIZE_SUFFIXES):
        unit = base ** (i + 2)
        if round((bytes_int / unit) * base) < base:
            return f"{base * bytes_int / unit:.1f} {suffix}"
    return None


def human_readable_to_bytes(value: str) -> int:
    """Convert a human readable size to bytes.

    Args:
        value: A string such as "10MB".  If a suffix is not included,
            then the value is assumed to be an integer representing the size
            in bytes.

    Returns:
        The converted value in bytes as an integer

    """
    value = value.lower()
    if value[-2:] == "ib":
        # Assume IEC suffix.
        suffix = value[-3:].lower()
    else:
        suffix = value[-2:].lower()
    has_size_identifier = len(value) >= 2 and suffix in SIZE_SUFFIX
    if not has_size_identifier:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid size value: {value}") from None
    else:
        multiplier = SIZE_SUFFIX[suffix]
        return int(value[: -len(suffix)]) * multiplier


@overload
def relative_path(filename: AnyPath, start: AnyPath = ...) -> str:
    ...


@overload
def relative_path(filename: None, start: AnyPath = ...) -> None:
    ...


@overload
def relative_path(filename: Optional[AnyPath], start: AnyPath = ...) -> Optional[str]:
    ...


def relative_path(
    filename: Optional[AnyPath], start: AnyPath = os.path.curdir
) -> Optional[str]:
    """Cross platform relative path of a filename.

    If no relative path can be calculated (i.e different
    drives on Windows), then instead of raising a ValueError,
    the absolute path is returned.

    """
    if not filename:
        return None
    try:
        dirname, basename = os.path.split(str(filename))
        relative_dir = os.path.relpath(dirname, start)
        return os.path.join(relative_dir, basename)
    except ValueError:
        return os.path.abspath(str(filename))


class SetFileUtimeError(Exception):
    """Set file update time error."""


def set_file_utime(filename: AnyPath, desired_time: float):
    """Set the utime of a file, and if it fails, raise a more explicit error.

    Args:
        filename: the file to modify
        desired_time: the epoch timestamp to set for atime and mtime.

    Raises:
        SetFileUtimeError: if you do not have permission (errno 1)
        OSError: for all errors other than errno 1

    """
    try:
        os.utime(filename, (desired_time, desired_time))
    except OSError as exc:
        # Only raise a more explicit exception when it is a permission issue.
        if exc.errno != errno.EPERM:
            raise
        raise SetFileUtimeError(
            "The file was downloaded, but attempting to modify the "
            "utime of the file failed. Is the file owned by another user?"
        ) from exc


def split_s3_bucket_key(s3_path: str) -> Tuple[str, str]:
    """Split s3 path into bucket and key prefix.

    This will also handle the s3:// prefix.

    Args:
        s3_path: Path to an object in S3 or object prefix.

    Returns:
        Bucket name, key

    """
    if s3_path.startswith("s3://"):
        s3_path = s3_path[5:]
    return find_bucket_key(s3_path)


def uni_print(statement: str, out_file: Optional[TextIO] = None) -> None:
    """Write unicode to a file, usually stdout or stderr.

    Ensures that the proper encoding is used if the statement is not a string type.

    """
    if out_file is None:
        out_file = sys.stdout
    try:
        out_file.write(statement)
    except UnicodeEncodeError:
        new_encoding = getattr(out_file, "encoding", "ascii")
        if not new_encoding:
            new_encoding = "ascii"
        new_statement = statement.encode(new_encoding, "replace").decode(new_encoding)
        out_file.write(new_statement)
    out_file.flush()
