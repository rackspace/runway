"""File info.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/fileinfo.py

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from ......compat import cached_property
from .utils import EPOCH_TIME

if TYPE_CHECKING:
    import datetime

    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef, ObjectTypeDef

    from ......type_defs import AnyPath
    from .format_path import SupportedPathType


class FileInfo:
    """Important details related to performing a task.

    It can perform operations such as ``upload``, ``download``, ``copy``,
    ``delete``, ``move``.  Similarly to ``TaskInfo`` objects attributes
    like ``session`` need to be set in order to perform operations.

    """

    def __init__(
        self,
        src: AnyPath,
        *,
        client: Optional[S3Client] = None,
        compare_key: Optional[str] = None,
        dest_type: Optional[SupportedPathType] = None,
        dest: Optional[AnyPath] = None,
        is_stream: bool = False,
        last_update: Optional[datetime.datetime] = None,
        operation_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        response_data: Optional[Union[HeadObjectOutputTypeDef, ObjectTypeDef]] = None,
        size: Optional[int] = None,
        source_client: Optional[S3Client] = None,
        src_type: Optional[SupportedPathType] = None,
    ) -> None:
        """Instantiate class.

        Args:
            src: Source path.
            client: boto3 S3 client.
            compare_key: The name of the file relative to the specified
                directory/prefix. This variable is used when performing synching
                or if the destination file is adopting the source file's name.
            dest_type: If the destination is s3 or local.
            dest: Destination path.
            is_stream: If the file is a stream.
            last_update: The local time of last modification.
            operation_name: Name of the operation being run.
            parameters: A dictionary of important values this is assigned in
                the ``BasicTask`` object.
            response_data: The response data used by
                the ``FileGenerator`` to create this task. It is either an dictionary
                from the list of a ListObjects or the response from a HeadObject. It
                will only be filled if the task was generated from an S3 bucket.
            size: The size of the file in bytes.
            source_client: Client to handle the source.
            src_type: If the source is s3 or local.

        """
        self.src = src
        self.src_type = src_type
        self.operation_name = operation_name
        self.client = client
        self.dest = dest
        self.dest_type = dest_type
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update or EPOCH_TIME
        self.parameters = parameters or {}
        self.source_client = source_client
        self.is_stream = is_stream
        self.associated_response_data = response_data

    @cached_property
    def is_glacier_compatible(self) -> bool:
        """Determine if a file info object is glacier compatible.

        Operations will fail if the S3 object has a storage class of GLACIER
        and it involves copying from S3 to S3, downloading from S3, or moving
        where S3 is the source (the delete will actually succeed, but we do
        not want fail to transfer the file and then successfully delete it).

        Returns:
            True if the FileInfo's operation will not fail because the
            operation is on a glacier object. False if it will fail.

        """
        if self._is_glacier_object(self.associated_response_data):
            if self.operation_name in ["copy", "download"]:
                return False
            if self.operation_name == "move" and self.src_type == "s3":
                return False
        return True

    def _is_glacier_object(
        self, response_data: Optional[Union[HeadObjectOutputTypeDef, ObjectTypeDef]]
    ) -> bool:
        """Determine if a file info object is glacier compatible."""
        glacier_storage_classes = ["GLACIER", "DEEP_ARCHIVE"]
        if response_data:
            if response_data.get(
                "StorageClass"
            ) in glacier_storage_classes and not self._is_restored(response_data):
                return True
        return False

    @staticmethod
    def _is_restored(
        response_data: Union[HeadObjectOutputTypeDef, ObjectTypeDef]
    ) -> bool:
        """Return True is this is a glacier object that has been restored back to S3."""
        # 'Restore' looks like: 'ongoing-request="false", expiry-date="..."'
        return 'ongoing-request="false"' in response_data.get("Restore", "")
