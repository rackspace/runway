"""Utility functions for S3."""
from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Sequence, cast

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.service_resource import S3ServiceResource
    from mypy_boto3_s3.type_defs import ObjectTypeDef

    from ._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def _get_client(
    session: Optional[boto3.Session] = None, region: Optional[str] = None
) -> S3Client:
    """Get S3 boto client."""
    return session.client("s3") if session else boto3.client("s3", region_name=region)


def _get_resource(
    session: Optional[boto3.Session] = None, region: Optional[str] = None
) -> S3ServiceResource:
    """Get S3 boto resource."""
    return (
        session.resource("s3") if session else boto3.resource("s3", region_name=region)
    )


def purge_and_delete_bucket(
    bucket_name: str, region: str = "us-east-1", session: Optional[boto3.Session] = None
) -> None:
    """Delete all objects and versions in bucket, then delete bucket."""
    purge_bucket(bucket_name, region, session)
    delete_bucket(bucket_name, region, session)


def purge_bucket(
    bucket_name: str, region: str = "us-east-1", session: Optional[boto3.Session] = None
) -> None:
    """Delete all objects and versions in bucket."""
    if does_bucket_exist(bucket_name, region, session):
        s3_resource = _get_resource(session, region)
        bucket = s3_resource.Bucket(bucket_name)
        bucket.object_versions.delete()
    else:
        LOGGER.warning('bucket "%s" does not exist in region "%s"', bucket_name, region)


def delete_bucket(
    bucket_name: str, region: str = "us-east-1", session: Optional[boto3.Session] = None
) -> None:
    """Delete bucket."""
    if does_bucket_exist(bucket_name, region, session):
        LOGGER.verbose('delete bucket "%s"...', bucket_name)
        s3_resource = _get_resource(session, region)
        bucket = s3_resource.Bucket(bucket_name)
        bucket.delete()
        LOGGER.info('delete bucket "%s"', bucket_name)
    else:
        LOGGER.warning('bucket "%s" does not exist in region "%s"', bucket_name, region)


def does_bucket_exist(
    bucket_name: str, region: str = "us-east-1", session: Optional[boto3.Session] = None
) -> bool:
    """Check if bucket exists in S3."""
    s3_resource = _get_resource(session, region)
    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Message"] == "Not Found":
            LOGGER.info('bucket "%s" does not exist', bucket_name)
            return False
        if exc.response["Error"]["Message"] == "Forbidden":
            LOGGER.exception(
                'access denied for bucket "%s" (permissions?)', bucket_name
            )
            raise
    return False


def ensure_bucket_exists(
    bucket_name: str, region: str = "us-east-1", session: Optional[boto3.Session] = None
) -> None:
    """Ensure S3 bucket exists."""
    if not does_bucket_exist(bucket_name, region, session):
        LOGGER.info('creating bucket "%s" (in progress)', bucket_name)
        s3_client = _get_client(session, region)
        if region == "us-east-1":
            create_bucket_opts: Dict[str, Any] = {}
        else:
            create_bucket_opts = {
                "CreateBucketConfiguration": {"LocationConstraint": region}
            }
        s3_client.create_bucket(Bucket=bucket_name, **create_bucket_opts)

        # sometimes when creating the bucket it can take a few moments before
        # it is ready to add the encryption settings.
        bucket_waiter = s3_client.get_waiter("bucket_exists")
        bucket_waiter.wait(Bucket=bucket_name)
        LOGGER.info('creating bucket "%s" (complete)', bucket_name)

        # enable default encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )
        LOGGER.verbose('enabled encryption for bucket "%s"', bucket_name)


def does_s3_object_exist(
    bucket: str,
    key: str,
    session: Optional[boto3.Session] = None,
    region: str = "us-east-1",
) -> bool:
    """Determine if object exists on s3."""
    s3_resource = _get_resource(session, region)
    try:
        s3_resource.Object(bucket, key).load()
        LOGGER.debug("s3 object exists: %s/%s", bucket, key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            LOGGER.debug("s3 object does not exist: %s/%s", bucket, key)
            return False
        raise
    return True


def upload(
    bucket: str, key: str, filename: str, session: Optional[boto3.Session] = None
) -> None:
    """Upload file to S3 bucket."""
    s3_client = _get_client(session)
    LOGGER.info("uploading %s to s3://%s/%s...", filename, bucket, key)
    s3_client.upload_file(Filename=filename, Bucket=bucket, Key=key)


def download(
    bucket: str, key: str, file_path: str, session: Optional[boto3.Session] = None
) -> str:
    """Download a file from S3 to the given path."""
    s3_client = _get_client(session)

    LOGGER.info("downloading s3://%s/%s to %s...", bucket, key, file_path)
    s3_client.download_file(Bucket=bucket, Key=key, Filename=file_path)
    return file_path


def download_and_extract_to_mkdtemp(
    bucket: str, key: str, session: Optional[boto3.Session] = None
) -> str:
    """Download zip archive and extract it to temporary directory."""
    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    download(bucket, key, temp_file, session)

    output_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(temp_file, "r") as zip_ref:
        zip_ref.extractall(output_dir)
    os.remove(temp_file)
    LOGGER.verbose("extracted %s to %s", temp_file, output_dir)
    return output_dir


def get_matching_s3_objects(
    bucket: str,
    prefix: Sequence[str] = "",
    suffix: str = "",
    session: Optional[boto3.Session] = None,
) -> Iterator[ObjectTypeDef]:
    """Generate objects in an S3 bucket.

    Args:
        bucket: Name of the S3 bucket.
        prefix: Only fetch objects whose key starts with
            this prefix (optional).
        suffix: Only fetch objects whose keys end with
            this suffix (optional).
        session: Boto3/botocore session.

    """
    s3_client = _get_client(session)
    paginator = s3_client.get_paginator("list_objects_v2")

    kwargs = {"Bucket": bucket}

    # We can pass the prefix directly to the S3 API.  If the user has passed
    # a tuple or list of prefixes, we go through them one by one.
    prefixes = (prefix,) if isinstance(prefix, str) else prefix
    for key_prefix in prefixes:
        kwargs["Prefix"] = key_prefix

        for page in paginator.paginate(**kwargs):
            try:
                contents = page["Contents"]
            except KeyError:
                return

            for obj in contents:
                if "Key" in obj and obj["Key"].endswith(suffix):
                    yield obj


def get_matching_s3_keys(
    bucket: str,
    prefix: str = "",
    suffix: str = "",
    session: Optional[boto3.Session] = None,
) -> Iterator[str]:
    """Generate the keys in an S3 bucket.

    Args:
        bucket: Name of the S3 bucket.
        prefix: Only fetch keys that start with this prefix (optional).
        suffix: Only fetch keys that end with this suffix (optional).
        session: Boto3/botocore session.

    """
    for obj in get_matching_s3_objects(bucket, prefix, suffix, session):
        if "Key" in obj:
            yield obj["Key"]
