"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

from ...utils import BaseModel

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class PurgeBucketHookArgs(BaseModel):
    """Hook arguments for ``purge_bucket``."""

    bucket_name: str
    """Name of the bucket to purge."""


def purge_bucket(context: CfnginContext, *__args: Any, **kwargs: Any) -> bool:
    """Delete objects in bucket."""
    args = PurgeBucketHookArgs.model_validate(kwargs)
    session = context.get_session()
    s3_resource = session.resource("s3")
    try:
        s3_resource.meta.client.head_bucket(Bucket=args.bucket_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            LOGGER.info('bucket "%s" does not exist; unable to complete purge', args.bucket_name)
            return True
        raise

    bucket = s3_resource.Bucket(args.bucket_name)
    bucket.object_versions.delete()
    return True
