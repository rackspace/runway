"""AWS S3 exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....exceptions import RunwayError

if TYPE_CHECKING:
    from . import Bucket


class BucketAccessDeniedError(RunwayError):
    """Access denied to S3 Bucket."""

    bucket_name: str
    """Name of the S3 Bucket."""

    def __init__(self, bucket: Bucket) -> None:
        """Instantiate class.

        Args:
            bucket: AWS S3 Bucket object.

        """
        self.bucket_name = bucket.name
        self.message = f"access denied for bucket {bucket.name}"
        super().__init__()


class BucketNotFoundError(RunwayError):
    """S3 Bucket not found."""

    bucket_name: str
    """Name of the S3 Bucket"""

    def __init__(self, bucket: Bucket) -> None:
        """Instantiate class.

        Args:
            bucket: AWS S3 Bucket object.

        """
        self.bucket_name = bucket.name
        self.message = f"bucket {bucket.name} not found"
        super().__init__()


class S3ObjectDoesNotExistError(RunwayError):
    """Required S3 object does not exist."""

    bucket: str
    """Name of the S3 Bucket"""

    key: str
    """S3 object key."""

    uri: str
    """S3 object URI."""

    def __init__(self, bucket: str, key: str) -> None:
        """Instantiate class.

        Args:
            bucket: Name of the S3 bucket.
            key: S3 object key.

        """
        self.bucket = bucket
        self.key = key
        self.uri = f"s3://{bucket}/{key.lstrip('/')}"
        self.message = f"S3 object does not exist at path {self.uri}"
        super().__init__()
