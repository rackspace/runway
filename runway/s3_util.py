"""Utility functions for S3."""
import logging
import os
import tempfile
import zipfile

import boto3
from boto3.s3.transfer import S3Transfer
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)


def _get_client(session=None, region=None):
    """Get S3 boto client."""
    return session.client("s3") if session else boto3.client("s3", region_name=region)


def _get_resource(session=None, region=None):
    """Get S3 boto resource."""
    return (
        session.resource("s3") if session else boto3.resource("s3", region_name=region)
    )


def purge_and_delete_bucket(bucket_name, region="us-east-1", session=None):
    """Delete all objects and versions in bucket, then delete bucket."""
    purge_bucket(bucket_name, region, session)
    delete_bucket(bucket_name, region, session)


def purge_bucket(bucket_name, region="us-east-1", session=None):
    """Delete all objects and versions in bucket."""
    if does_bucket_exist(bucket_name, region, session):
        s3_resource = _get_resource(session, region)
        bucket = s3_resource.Bucket(bucket_name)
        bucket.object_versions.delete()
    else:
        LOGGER.warning('bucket "%s" does not exist in region "%s"', bucket_name, region)


def delete_bucket(bucket_name, region="us-east-1", session=None):
    """Delete bucket."""
    if does_bucket_exist(bucket_name, region, session):
        LOGGER.verbose('delete bucket "%s"...', bucket_name)
        s3_resource = _get_resource(session, region)
        bucket = s3_resource.Bucket(bucket_name)
        bucket.delete()
        LOGGER.info('delete bucket "%s"', bucket_name)
    else:
        LOGGER.warning('bucket "%s" does not exist in region "%s"', bucket_name, region)


def does_bucket_exist(bucket_name, region="us-east-1", session=None):
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


def ensure_bucket_exists(bucket_name, region="us-east-1", session=None):
    """Ensure S3 bucket exists."""
    if not does_bucket_exist(bucket_name, region, session):
        LOGGER.info('creating bucket "%s" (in progress)', bucket_name)
        s3_client = _get_client(session, region)
        if region == "us-east-1":
            create_bucket_opts = {}
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


def does_s3_object_exist(bucket, key, session=None, region="us-east-1"):
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


def upload(bucket, key, filename, session=None):
    """Upload file to S3 bucket."""
    s3_client = _get_client(session)
    LOGGER.info("uploading %s to s3://%s/%s...", filename, bucket, key)
    s3_client.upload_file(filename, bucket, key)


def download(bucket, key, file_path, session=None):
    """Download a file from S3 to the given path."""
    s3_client = _get_client(session)

    transfer = S3Transfer(s3_client)
    LOGGER.info("downloading s3://%s/%s to %s...", bucket, key, file_path)
    transfer.download_file(bucket, key, file_path)
    return file_path


def download_and_extract_to_mkdtemp(bucket, key, session=None):
    """Download zip archive and extract it to temporary directory."""
    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    download(bucket, key, temp_file, session)

    output_dir = tempfile.mkdtemp()
    zip_ref = zipfile.ZipFile(temp_file, "r")
    zip_ref.extractall(output_dir)
    zip_ref.close()
    os.remove(temp_file)
    LOGGER.verbose("extracted %s to %s", temp_file, output_dir)
    return output_dir


def get_matching_s3_objects(bucket, prefix="", suffix="", session=None):
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
    if isinstance(prefix, str):
        prefixes = (prefix,)
    else:
        prefixes = prefix

    for key_prefix in prefixes:
        kwargs["Prefix"] = key_prefix

        for page in paginator.paginate(**kwargs):
            try:
                contents = page["Contents"]
            except KeyError:
                return

            for obj in contents:
                key = obj["Key"]
                if key.endswith(suffix):
                    yield obj


def get_matching_s3_keys(bucket, prefix="", suffix="", session=None):
    """Generate the keys in an S3 bucket.

    Args:
        bucket: Name of the S3 bucket.
        prefix: Only fetch keys that start with this prefix (optional).
        suffix: Only fetch keys that end with this suffix (optional).
        session: Boto3/botocore session.

    """
    for obj in get_matching_s3_objects(bucket, prefix, suffix, session):
        yield obj["Key"]
