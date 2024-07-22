"""Cleanup S3 Bucket."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from runway.core.providers.aws.s3 import Bucket

if TYPE_CHECKING:
    from _typeshed import StrPath

    from runway.context import CfnginContext

LOGGER = logging.getLogger("runway.cfngin.hooks.custom.cleanup")


def local_delete(
    context: CfnginContext,  # noqa: ARG001
    *,
    path: StrPath,
    **_: Any,
) -> bool:
    """Delete local path."""
    abs_path = Path(path).resolve()
    LOGGER.info("deleting local path %s...", abs_path)
    shutil.rmtree(abs_path, ignore_errors=True)
    return True


def s3_delete_prefix(
    context: CfnginContext,
    *,
    bucket_name: str,
    delimiter: str = "/",
    prefix: str,
    **_: Any,
) -> bool:
    """Delete all S3 Objects with prefix."""
    if not Bucket(context, bucket_name):
        LOGGER.warning("bucket '%s' does not exist or you do not have access to it")
        return True
    bucket = context.get_session().resource("s3").Bucket(bucket_name)
    LOGGER.info(
        "deleting objects from s3://%s%s%s...",
        bucket_name,
        delimiter,
        prefix,
    )
    bucket.object_versions.filter(Delimiter=delimiter, Prefix=prefix).delete()
    return True
