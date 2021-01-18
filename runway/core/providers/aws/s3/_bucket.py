"""AWS S3 bucket."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional, Union

from botocore.exceptions import ClientError

from .....util import cached_property
from .._response import BaseResponse

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import (
        CreateBucketOutputTypeDef,
        GetBucketVersioningOutputTypeDef,
    )

    from .....cfngin.context import Context as CFNginContext
    from .....context import Context as RunwayContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class Bucket:
    """AWS S3 bucket."""

    def __init__(
        self,
        context: Union[CFNginContext, RunwayContext],
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
        return self.__ctx.get_session(region=self._region).client("s3")

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

    def create(self, **kwargs: Any) -> CreateBucketOutputTypeDef:
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
            return {}
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
            Bucket=self.name, VersioningConfiguration=config
        )
        LOGGER.debug('enabled versioning for bucket "%s"', self.name)

    def get_versioning(self) -> GetBucketVersioningOutputTypeDef:
        """Get the versioning state of a bucket.

        To retrieve the versioning state of a bucket, you must be the bucket owner.

        Returns:
            The current versioning state of the bucket containing ``Status``
            and ``MFADelete`` (only if this has ever been configured).

        """
        return self.client.get_bucket_versioning(Bucket=self.name)
