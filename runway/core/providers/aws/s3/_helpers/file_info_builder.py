"""File info builder.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/fileinfobuilder.py

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator, Iterable, Optional

from .file_info import FileInfo

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

    from .file_generator import FileStats
    from .parameters import ParametersDataModel


class FileInfoBuilder:
    """Takes a ``FileStats`` object's attributes and generates a ``FileInfo`` object."""

    def __init__(
        self,
        *,
        client: S3Client,
        is_stream: bool = False,
        parameters: Optional[ParametersDataModel] = None,
        source_client: Optional[Any] = None,
    ) -> None:
        """Instantiate class.

        Args:
            client: boto3 S3 client.
            is_stream: If the file is a stream.
            parameters: A dictionary of important values this is assigned in
                the ``BasicTask`` object.
            source_client: Client to handle the source.

        """
        self._client = client
        self._source_client = client
        if source_client is not None:
            self._source_client = source_client
        self._parameters = parameters
        self._is_stream = is_stream

    def call(self, files: Iterable[FileStats]) -> Generator[FileInfo, None, None]:
        """Iterate generator of ``FileStats`` to generate ``FileInfo`` objects."""
        for file_base in files:
            file_info = self._inject_info(file_base)
            yield file_info

    def _inject_info(self, file_base: FileStats) -> FileInfo:
        """Inject info.

        Args:
            file_base: File stats to include in the FileInfo object.

        """
        delete_enabled = self._parameters.delete if self._parameters else False
        return FileInfo(
            **file_base.dict(),
            **{"client": self._source_client, "source_client": self._client}
            if file_base.operation_name == "delete" and delete_enabled
            else {"client": self._client, "source_client": self._source_client},
        )
