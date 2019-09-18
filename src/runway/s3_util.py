"""Utility functions for S3."""
import logging
import tempfile
import os
import zipfile
import boto3

from boto3.s3.transfer import S3Transfer
from botocore.exceptions import ClientError

LOGGER = logging.getLogger('runway')


def _get_client(session=None):
    """Get S3 boto client."""
    return session.client('s3') if session else boto3.client('s3')


def _get_resource(session=None):
    """Get S3 boto resource."""
    return session.resource('s3') if session else boto3.resource('s3')


def ensure_bucket_exists(bucket_name, region=None):
    """Ensure S3 bucket exists."""
    if region is None:
        region = 'us-east-1'

    s3_resource = boto3.resource('s3', region_name=region)

    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        if exc.response['Error']['Message'] == 'Not Found':
            LOGGER.info("Bucket \"%s\" does not exist, creating...", bucket_name)
            s3_client = boto3.client('s3', region_name=region)
            if region == 'us-east-1':
                create_bucket_opts = {}
            else:
                create_bucket_opts = {
                    'CreateBucketConfiguration': {
                        'LocationConstraint': region
                    }
                }
            s3_client.create_bucket(Bucket=bucket_name, **create_bucket_opts)

            # enable default encryption
            s3_client.put_bucket_encryption(Bucket=bucket_name,
                                            ServerSideEncryptionConfiguration={
                                                'Rules': [{
                                                    'ApplyServerSideEncryptionByDefault': {
                                                        'SSEAlgorithm': 'AES256'
                                                    }
                                                }]
                                            })
        elif exc.response['Error']['Message'] == 'Forbidden':
            LOGGER.exception("Access denied for bucket %s (name conflict?)",
                             bucket_name)
            raise
        else:
            LOGGER.exception("Error creating bucket %s. Error %s",
                             bucket_name, exc.response)
            raise


def does_s3_object_exist(bucket, key, session=None):
    """Determine if object exists on s3."""
    s3_resource = _get_resource(session)

    try:
        s3_resource.Object(bucket, key).load()
    except ClientError as exc:
        if exc.response['Error']['Code'] == '404':
            return False
        raise
    return True


def upload(bucket, key, filename, session=None):
    """Upload file to S3 bucket."""
    s3_client = _get_client(session)
    LOGGER.info('Uploading %s to %s/%s', filename, bucket, key)
    s3_client.upload_file(filename, bucket, key)


def download(bucket, key, file_path, session=None):
    """Download a file from S3 to the given path."""
    s3_client = _get_client(session)

    transfer = S3Transfer(s3_client)
    transfer.download_file(bucket, key, file_path)
    return file_path


def download_and_extract_to_mkdtemp(bucket, key, session=None):
    """Download zip archive and extract it to temporary directory."""
    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    download(bucket, key, temp_file, session)

    output_dir = tempfile.mkdtemp()
    zip_ref = zipfile.ZipFile(temp_file, 'r')
    zip_ref.extractall(output_dir)
    zip_ref.close()
    os.remove(temp_file)
    return output_dir
