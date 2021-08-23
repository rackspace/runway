"""File generator.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/filegenerator.py

"""
from __future__ import annotations

import datetime
import os
import stat
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from botocore.exceptions import ClientError
from dateutil.parser import parse
from dateutil.tz import tzlocal
from typing_extensions import TypedDict

from .utils import (
    EPOCH_TIME,
    BucketLister,
    create_warning,
    find_bucket_key,
    find_dest_path_comp_key,
    get_file_stat,
)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef, ObjectTypeDef

    from ......type_defs import AnyPath
    from .format_path import FormatPathResult, SupportedPathType


def is_readable(path: Path) -> bool:
    """Check to see if a file or a directory can be read.

    This is tested by performing an operation that requires read access
    on the file or the directory.

    """
    if path.is_dir():
        try:
            os.listdir(path)
        except OSError:
            return False
    else:
        try:
            with open(path, "r", encoding="utf-8"):
                pass
        except OSError:
            return False
    return True


def is_special_file(path: Path) -> bool:
    """Check to see if a special file.

    It checks if the file is a character special device, block special device,
    FIFO, or socket.

    """
    mode = path.stat().st_mode
    # Character special device.
    if stat.S_ISCHR(mode):
        return True
    # Block special device
    if stat.S_ISBLK(mode):
        return True
    # FIFO.
    if stat.S_ISFIFO(mode):
        return True
    # Socket.
    if stat.S_ISSOCK(mode):
        return True
    return False


FileStatsDict = TypedDict(
    "FileStatsDict",
    src="AnyPath",
    compare_key=Optional[str],
    dest_type=Optional["SupportedPathType"],
    dest=Optional[str],
    last_update=datetime.datetime,
    operation_name=Optional[str],
    response_data=Optional[Union["HeadObjectOutputTypeDef", "ObjectTypeDef"]],
    size=Optional[int],
    src_type=Optional["SupportedPathType"],
)


@dataclass
class FileStats:
    """Information about a file.

    Attributes:
        src: Path to source file or S3 object.
        compare_key: The name of the file relative to the specified
                directory/prefix. This variable is used when performing synching
                or if the destination file is adopting the source file's name.
        dest_type: Location of the destination - either local or S3.
        dest: Path to destination file or S3 object.
        last_update: Timestamp when file or S3 object was last updated.
        operation_name: Name of the operation being run.
        response_data: S3 object metadata. Only set if dest_type == S3.
        size: Size of the file or S3 object in bytes.
        src_type: Location of the source - either local or S3.

    """

    src: AnyPath
    compare_key: Optional[str] = None
    dest: Optional[str] = None
    dest_type: Optional[SupportedPathType] = None
    last_update: datetime.datetime = EPOCH_TIME
    operation_name: Optional[str] = None
    response_data: Optional[Union[HeadObjectOutputTypeDef, ObjectTypeDef]] = None
    size: Optional[int] = None
    src_type: Optional[SupportedPathType] = None

    def dict(self) -> FileStatsDict:
        """Dump contents of object to a dict."""
        return deepcopy(cast(FileStatsDict, self.__dict__))


_LastModifiedAndSize = TypedDict(
    "_LastModifiedAndSize", Size=int, LastModified=datetime.datetime
)


class FileGenerator:
    """Create a generator to yield files.

    It is universal in the sense that it will handle s3 files, local files,
    local directories, and s3 objects under the same common prefix.

    """

    result_queue: "Queue[Any]"

    def __init__(
        self,
        client: S3Client,
        operation_name: str,
        follow_symlinks: bool = True,
        page_size: Optional[int] = None,
        result_queue: Optional["Queue[Any]"] = None,
        request_parameters: Any = None,
    ):
        """Instantiate class.

        Args:
            client: boto3 S3 client.
            operation_name: Name of the operation being executed.
            follow_symlinks: If symlinks should be followed.
            page_size: Number of items per page.
            result_queue: Queue used for outputing results.
            request_parameters: Parameters provided with the request.

        """
        self._client = client
        self.operation_name = operation_name
        self.follow_symlinks = follow_symlinks
        self.page_size = page_size
        self.result_queue = result_queue or Queue()
        self.request_parameters = {}
        if request_parameters is not None:
            self.request_parameters = request_parameters

    def call(self, files: FormatPathResult) -> Generator[FileStats, None, None]:
        """Generalized function to yield the ``FileInfo`` objects."""
        function_table = {"s3": self.list_objects, "local": self.list_files}
        file_iterator = function_table[files["src"]["type"]](
            files["src"]["path"], files["dir_op"]
        )
        for src_path, extra_information in file_iterator:
            dest_path, compare_key = find_dest_path_comp_key(files, src_path)
            file_stat_kwargs: FileStatsDict = {
                "compare_key": compare_key,
                "dest": dest_path,
                "dest_type": files["dest"]["type"],
                "last_update": extra_information.get("LastModified", EPOCH_TIME),
                "operation_name": self.operation_name,
                "response_data": None,
                "size": extra_information.get("Size", 0),
                "src": src_path,
                "src_type": files["src"]["type"],
            }
            if files["src"]["type"] == "s3":
                file_stat_kwargs["response_data"] = cast(
                    Optional[Union["HeadObjectOutputTypeDef", "ObjectTypeDef"]],
                    extra_information,
                )
            yield FileStats(**file_stat_kwargs)

    def list_files(
        self, path: AnyPath, dir_op: bool
    ) -> Generator[Tuple[Path, _LastModifiedAndSize], None, None]:
        """Yield the appropriate local file or local files under a directory.

        For directories a depth first search is implemented in order to
        follow the same sorted pattern as a s3 list objects operation
        outputs. It yields the file's source path, size, and last
        update.

        """
        if isinstance(path, str):
            path = Path(path)
        if not self.should_ignore_file(path):
            if not dir_op:
                stats = self.safely_get_file_stats(path)
                if stats:
                    yield stats
            else:
                # using os.listdir instead of Path.iterdir so we can sort the list
                # but not load the entire tree into memory
                listdir_names = os.listdir(path)
                names: List[str] = []
                for name in listdir_names:
                    if (path / name).is_dir():
                        name = name + os.path.sep
                    names.append(name)
                self.normalize_sort(names, os.sep, "/")
                for name in names:
                    file_path = path / name
                    if file_path.is_dir():
                        for result in self.list_files(file_path, dir_op):
                            yield result
                    else:
                        stats = self.safely_get_file_stats(file_path)
                        if stats:
                            yield stats

    @staticmethod
    def normalize_sort(names: List[str], os_sep: str, character: str) -> None:
        """Ensure that the same path seperator is used when sorting.

        On Windows, the path operator is a backslash as opposed to a forward slash
        which can lead to differences in sorting between S3 and a Windows machine.

        Args:
            names: List of file names.
            os_sep: OS seperator.
            character: Character that will be used to replace the os_sep.

        """
        names.sort(key=lambda item: item.replace(os_sep, character))

    def safely_get_file_stats(
        self, path: Path
    ) -> Optional[Tuple[Path, _LastModifiedAndSize]]:
        """Get file stats with handling for some common errors.

        Args:
            path: Path to a file.

        """
        try:
            size, last_update = get_file_stat(path)
        except (OSError, ValueError):
            self.triggers_warning(path)
        else:
            last_update = self._validate_update_time(last_update, path)
            return path, {"Size": size, "LastModified": last_update}
        return None

    def _validate_update_time(
        self, update_time: Optional[datetime.datetime], path: Path
    ) -> datetime.datetime:
        """Handle missing last modified time."""
        if update_time is None:
            warning = create_warning(
                path=path,
                error_message="File has an invalid timestamp. Passing epoch "
                "time as timestamp.",
                skip_file=False,
            )
            self.result_queue.put(warning)
            return EPOCH_TIME
        return update_time

    def should_ignore_file(self, path: Path) -> bool:
        """Check whether a file should be ignored in the file generation process.

        This includes symlinks that are not to be followed and files that generate
        warnings.

        """
        if not self.follow_symlinks:
            if path.is_dir() and path.is_symlink():
                # is_symlink returns False if it does not exist
                return True
        warning_triggered = self.triggers_warning(path)
        if warning_triggered:
            return True
        return False

    def triggers_warning(self, path: Path) -> bool:
        """Check the specific types and properties of a file.

        If the file would cause trouble, the function adds a
        warning to the result queue to be printed out and returns a boolean
        value notify whether the file caused a warning to be generated.
        Files that generate warnings are skipped. Currently, this function
        checks for files that do not exist and files that the user does
        not have read access.

        """
        if not path.exists():
            warning = create_warning(path, "File does not exist.")
            self.result_queue.put(warning)
            return True
        if is_special_file(path):
            warning = create_warning(
                path,
                (
                    "File is character special device, "
                    "block special device, FIFO, or socket."
                ),
            )
            self.result_queue.put(warning)
            return True
        if not is_readable(path):
            warning = create_warning(path, "File/Directory is not readable.")
            self.result_queue.put(warning)
            return True
        return False

    def list_objects(
        self, s3_path: str, dir_op: bool
    ) -> Generator[
        Tuple[str, Union[HeadObjectOutputTypeDef, ObjectTypeDef]], None, None
    ]:
        """Yield the appropriate object or objects under a common prefix.

        It yields the file's source path, size, and last update.

        Args:
            s3_path: Path to list.
            dir_op: If the path is a directory.

        """
        # Short circuit path: if we are not recursing into the s3
        # bucket and a specific path was given, we can just yield
        # that path and not have to call any operation in s3.
        bucket, prefix = find_bucket_key(s3_path)
        if not dir_op and prefix:
            yield self._list_single_object(s3_path)
        else:
            lister = BucketLister(self._client)
            extra_args: Any = self.request_parameters.get("ListObjectsV2", {})
            for obj in lister.list_objects(
                bucket=bucket,
                prefix=prefix,
                page_size=self.page_size,
                extra_args=extra_args,
            ):
                source_path, response_data = obj
                if response_data.get("Size", 0) == 0 and source_path.endswith("/"):
                    if self.operation_name == "delete":
                        # This is to filter out manually created folders
                        # in S3.  They have a size zero and would be
                        # undesirably downloaded.  Local directories
                        # are automatically created when they do not
                        # exist locally.  But user should be able to
                        # delete them.
                        yield source_path, response_data
                elif not dir_op and s3_path != source_path:
                    pass
                else:
                    yield source_path, response_data

    def _list_single_object(self, s3_path: str) -> Tuple[str, HeadObjectOutputTypeDef]:
        """List single object."""
        # When we know we're dealing with a single object, we can avoid
        # a ListObjects operation (which causes concern for anyone setting
        # IAM policies with the smallest set of permissions needed) and
        # instead use a HeadObject request.
        if self.operation_name == "delete":
            # If the operation is just a single remote delete, there is
            # no need to run HeadObject on the S3 object as none of the
            # information gained from HeadObject is required to delete the
            # object.
            return s3_path, {"Size": None, "LastModified": None}  # type: ignore
        bucket, key = find_bucket_key(s3_path)
        try:
            params: Dict[str, Any] = {"Bucket": bucket, "Key": key}
            # params.update(self.request_parameters.get("HeadObject", {}))
            response = self._client.head_object(**params)
        except ClientError as exc:
            # We want to try to give a more helpful error message.
            # This is what the customer is going to see so we want to
            # give as much detail as we have.
            if not exc.response["Error"]["Code"] == "404":
                raise
            # The key does not exist so we'll raise a more specific
            # error message here.
            response = exc.response.copy()
            response["Error"]["Message"] = f'Key "{key}" does not exist'
            raise ClientError(response, "HeadObject") from None
        response["Size"] = int(response.pop("ContentLength"))  # type: ignore
        last_update = parse(response["LastModified"])  # type: ignore
        response["LastModified"] = last_update.astimezone(tzlocal())
        return s3_path, response
