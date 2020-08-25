"""AWS S3 bucket."""
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Union  # pylint: disable=W

from botocore.exceptions import ClientError

from .....util import cached_property
from .._response import BaseResponse

if TYPE_CHECKING:
    from .....cfngin.context import Context as CFNginContext  # pylint: disable=W
    from .....context import Context as RunwayContext  # pylint: disable=W

LOGGER = logging.getLogger(__name__.replace("._", "."))


class Bucket(object):
    """AWS S3 bucket."""

    def __init__(
        self,
        context,  # type: Union[CFNginContext, RunwayContext]
        name,  # type: str
        region=None,  # type: Optional[str]
    ):
        # type: (...) -> None
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
    def client(self):
        """Create or reuse a boto3 client."""
        return self.__ctx.get_session(region=self._region).client("s3")

    @property
    def exists(self):
        # type: () -> bool
        """Check whether the bucket exists.

        Opposite of not_found.

        """
        return not self.not_found

    @cached_property
    def forbidden(self):
        # type: () -> bool
        """Check whether access to the bucket is forbidden."""
        return self.head.metadata.forbidden

    @cached_property
    def head(self):
        # type: () -> BaseResponse
        """Check if a bucket exists and you have permission to access it.

        To use this operation, the user must have permissions to perform the
        ``s3:ListBucket`` action.

        This is a low level action that returns the raw result of the request.

        """
        try:
            return BaseResponse(**self.client.head_bucket(Bucket=self.name))
        except ClientError as err:
            LOGGER.debug(
                'received an error from AWS S3 when trying to head bucket "%s"',
                self.name,
                exc_info=bool,
            )
            return BaseResponse(**err.response)

    @cached_property
    def not_found(self):
        # type: () -> bool
        """Check whether the bucket exists."""
        return self.head.metadata.not_found

    def create(self, **kwargs):
        # type: (Any) -> Dict[str, Any]
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

    def enable_versioning(self):
        # type: () -> None
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

    def get_versioning(self):
        # type: () -> Dict[str, str]
        """Get the versioning state of a bucket.

        To retrieve the versioning state of a bucket, you must be the bucket owner.

        Returns:
            The current versioning state of the bucket containing ``Status``
            and ``MFADelete`` (only if this has ever been configured).

        """
        return self.client.get_bucket_versioning(Bucket=self.name)
