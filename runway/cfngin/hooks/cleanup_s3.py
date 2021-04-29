"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


def purge_bucket(context: CfnginContext, *, bucket_name: str, **_: Any) -> bool:
    """Delete objects in bucket."""
    session = context.get_session()
    s3_resource = session.resource("s3")
    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            LOGGER.info(
                'bucket "%s" does not exist; unable to complete purge', bucket_name
            )
            return True
        raise

    bucket = s3_resource.Bucket(bucket_name)
    bucket.object_versions.delete()
    return True
