"""AWS S3 bucket."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, List, Optional, Union

from botocore.exceptions import ClientError

from .....compat import cached_property
from .._response import BaseResponse
from ._sync_handler import S3SyncHandler

if TYPE_CHECKING:
    import boto3
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import (
        CreateBucketOutputTypeDef,
        GetBucketVersioningOutputTypeDef,
    )

    from .....context import CfnginContext, RunwayContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class Bucket:
    """AWS S3 bucket."""

    def __init__(
        self,
        context: Union[CfnginContext, RunwayContext],
        name: str,
        region: Optional[str] = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Current context object.
            name: The name of the bucket.
            region: The bucket's region.

        """
        self.__ctx = context
        self._region = region
        self.name = name

    @cached_property
    def client(self) -> S3Client:
        """Create or reuse a boto3 client."""
        return self.session.client("s3")

    @property
    def exists(self) -> bool:
        """Check whether the bucket exists.

        Opposite of not_found.

        """
        return not self.not_found

    @cached_property
    def forbidden(self) -> bool:
        """Check whether access to the bucket is forbidden."""
        return self.head.metadata.forbidden

    @cached_property
    def head(self):
        """Check if a bucket exists and you have permission to access it.

        To use this operation, the user must have permissions to perform the
        ``s3:ListBucket`` action.

        This is a low level action that returns the raw result of the request.

        """
        try:
            return BaseResponse(**self.client.head_bucket(Bucket=self.name) or {})
        except ClientError as err:
            LOGGER.debug(
                'received an error from AWS S3 when trying to head bucket "%s"',
                self.name,
                exc_info=True,
            )
            return BaseResponse(**err.response)

    @cached_property
    def not_found(self) -> bool:
        """Check whether the bucket exists."""
        return self.head.metadata.not_found

    @cached_property
    def session(self) -> boto3.Session:
        """Create cached boto3 session."""
        return self.__ctx.get_session(region=self._region)

    def create(self, **kwargs: Any) -> Optional[CreateBucketOutputTypeDef]:
        """Create an S3 Bucket if it does not already exist.

        Bucket creation will be skipped if it already exists or access is forbidden.

        Keyword arguments are passed directly to the boto3 method.

        Returns:
            boto3 response.

        """
        if self.forbidden or self.exists:
            LOGGER.debug(
                'skipped creating bucket "%s": %s',
                self.name,
                "access denied" if self.forbidden else "bucket already exists",
            )
            return None
        kwargs["Bucket"] = self.name
        if self.client.meta.region_name != "us-east-1":
            kwargs.setdefault("CreateBucketConfiguration", {})
            kwargs["CreateBucketConfiguration"].update(
                {"LocationConstraint": self.client.meta.region_name}
            )
        LOGGER.debug("creating bucket: %s", json.dumps(kwargs))
        del self.not_found  # clear cached value
        del self.forbidden  # clear cached value
        del self.head  # clear cached value
        return self.client.create_bucket(**kwargs)

    def enable_versioning(self) -> None:
        """Enable versioning on the bucket if not already enabled."""
        config = self.get_versioning()
        if config.get("Status") == "Enabled":
            LOGGER.debug(
                'did not modify versioning policy for bucket "%s"; already enabled',
                self.name,
            )
            return
        config["Status"] = "Enabled"
        self.client.put_bucket_versioning(
            Bucket=self.name,
            VersioningConfiguration={
                "Status": "Enabled",
                "MFADelete": config.get("MFADelete", "Disabled"),
            },
        )
        LOGGER.debug('enabled versioning for bucket "%s"', self.name)

    def format_bucket_path_uri(
        self, *, key: Optional[str] = None, prefix: Optional[str] = None
    ) -> str:
        """Format bucket path URI.

        Args:
            key: S3 object key.
            prefix: Directory tree to append to key.

        Returns:
            S3 bucket URI in ``s3://{bucket-name}/{prefix}/{key}`` format

        """
        uri = f"s3://{self.name}"
        if prefix:
            uri += f"/{prefix}"
        if key:
            uri += f"/{key}"
        return uri

    def get_versioning(self) -> GetBucketVersioningOutputTypeDef:
        """Get the versioning state of a bucket.

        To retrieve the versioning state of a bucket, you must be the bucket owner.

        Returns:
            The current versioning state of the bucket containing ``Status``
            and ``MFADelete`` (only if this has ever been configured).

        """
        return self.client.get_bucket_versioning(Bucket=self.name)

    def sync_from_local(
        self,
        src_directory: str,
        *,
        delete: bool = False,
        exclude: Optional[List[str]] = None,
        follow_symlinks: bool = False,
        include: Optional[List[str]] = None,
        prefix: Optional[str] = None,
    ) -> None:
        """Sync local directory to the S3 Bucket.

        Args:
            src_directory: Local directory to sync to S3.
            delete: If true, files that exist in the destination but not in the
                source are deleted.
            exclude: List of patterns for files/objects to exclude.
            follow_symlinks: If symlinks should be followed.
            include: List of patterns for files/objects to explicitly include.
            prefix: Optional prefix to append to synced objects.

        """
        S3SyncHandler(
            context=self.__ctx,
            delete=delete,
            dest=self.format_bucket_path_uri(prefix=prefix),
            exclude=exclude,
            follow_symlinks=follow_symlinks,
            include=include,
            session=self.session,
            src=src_directory,
        ).run()

    def sync_to_local(
        self,
        dest_directory: str,
        *,
        delete: bool = False,
        exclude: Optional[List[str]] = None,
        follow_symlinks: bool = False,
        include: Optional[List[str]] = None,
        prefix: Optional[str] = None,
    ) -> None:
        """Sync S3 bucket to local directory.

        Args:
            dest_directory: Local directory to sync S3 objects to.
            delete: If true, files that exist in the destination but not in the
                source are deleted.
            exclude: List of patterns for files/objects to exclude.
            follow_symlinks: If symlinks should be followed.
            include: List of patterns for files/objects to explicitly include.
            prefix: Optional prefix to append to synced objects.

        """
        S3SyncHandler(
            context=self.__ctx,
            delete=delete,
            dest=dest_directory,
            exclude=exclude,
            follow_symlinks=follow_symlinks,
            include=include,
            session=self.session,
            src=self.format_bucket_path_uri(prefix=prefix),
        ).run()
