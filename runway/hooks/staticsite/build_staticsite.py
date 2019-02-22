"""Stacker hook for building static website."""

import logging
import os
import tempfile
import zipfile

from boto3.s3.transfer import S3Transfer
import boto3

from botocore.exceptions import ClientError
from stacker.lookups.handlers.rxref import RxrefLookup
from stacker.session_cache import get_session

from .util import get_hash_of_files
from ...util import change_dir, run_commands

LOGGER = logging.getLogger(__name__)


def does_s3_object_exist(bucket_name, key, session=None):
    """Determine if object exists on s3."""
    if session:
        s3_resource = session.resource('s3')
    else:
        s3_resource = boto3.resource('s3')

    try:
        s3_resource.Object(bucket_name, key).load()
    except ClientError as exc:
        if exc.response['Error']['Code'] == '404':
            return False
        raise
    return True


def download_and_extract_to_mkdtemp(bucket, key, session=None):
    """Download zip archive and extract it to temporary directory."""
    if session:
        s3_client = session.client('s3')
    else:
        s3_client = boto3.client('s3')
    transfer = S3Transfer(s3_client)

    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    transfer.download_file(bucket, key, temp_file)

    output_dir = tempfile.mkdtemp()
    zip_ref = zipfile.ZipFile(temp_file, 'r')
    zip_ref.extractall(output_dir)
    zip_ref.close()
    os.remove(temp_file)
    return output_dir


def zip_and_upload(app_dir, bucket, key, session=None):
    """Zip built static site and upload to S3."""
    if session:
        s3_client = session.client('s3')
    else:
        s3_client = boto3.client('s3')
    transfer = S3Transfer(s3_client)

    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    LOGGER.info("staticsite: archiving app at %s to s3://%s/%s",
                app_dir, bucket, key)
    with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as filehandle:
        with change_dir(app_dir):
            for dirname, _subdirs, files in os.walk('./'):
                if dirname != './':
                    filehandle.write(dirname)
                for filename in files:
                    filehandle.write(os.path.join(dirname, filename))
    transfer.upload_file(temp_file, bucket, key)
    os.remove(temp_file)


def build(context, provider, **kwargs):  # pylint: disable=unused-argument
    """Build static site."""
    session = get_session(provider.region)
    options = kwargs.get('options', {})
    context_dict = {}
    context_dict['artifact_key_prefix'] = "%s-%s-" % (options['namespace'], options['name'])  # noqa
    default_param_name = "%shash" % context_dict['artifact_key_prefix']

    if options.get('build_output'):
        build_output = os.path.join(
            options['path'],
            options['build_output']
        )
    else:
        build_output = options['path']

    context_dict['artifact_bucket_name'] = RxrefLookup.handle(
        kwargs.get('artifact_bucket_rxref_lookup'),
        provider=provider,
        context=context
    )

    if options.get('pre_build_steps'):
        run_commands(options['pre_build_steps'], options['path'])

    context_dict['hash'] = get_hash_of_files(
        root_path=options['path'],
        directories=options.get('source_hashing', {}).get('directories')
    )

    # Now determine if the current staticsite has already been deployed
    if options.get('source_hashing', {}).get('enabled', True):
        context_dict['hash_tracking_parameter'] = options.get(
            'source_hashing', {}).get('parameter', default_param_name)

        ssm_client = session.client('ssm')

        try:
            old_parameter_value = ssm_client.get_parameter(
                Name=context_dict['hash_tracking_parameter']
            )['Parameter']['Value']
        except ssm_client.exceptions.ParameterNotFound:
            old_parameter_value = None
    else:
        context_dict['hash_tracking_disabled'] = True
        old_parameter_value = None

    context_dict['current_archive_filename'] = (
        context_dict['artifact_key_prefix'] + context_dict['hash'] + '.zip'
    )
    if old_parameter_value:
        context_dict['old_archive_filename'] = (
            context_dict['artifact_key_prefix'] + old_parameter_value + '.zip'
        )

    if old_parameter_value == context_dict['hash']:
        LOGGER.info("staticsite: skipping build; app hash %s already deployed "
                    "in this environment",
                    context_dict['hash'])
        context_dict['deploy_is_current'] = True
        return context_dict

    if does_s3_object_exist(context_dict['artifact_bucket_name'],
                            context_dict['current_archive_filename'],
                            session):
        context_dict['app_directory'] = download_and_extract_to_mkdtemp(
            context_dict['artifact_bucket_name'],
            context_dict['current_archive_filename'], session
        )
    else:
        if options.get('build_steps'):
            LOGGER.info('staticsite: executing build commands')
            run_commands(options['build_steps'], options['path'])
        zip_and_upload(build_output, context_dict['artifact_bucket_name'],
                       context_dict['current_archive_filename'], session)
        context_dict['app_directory'] = build_output

    context_dict['deploy_is_current'] = False
    return context_dict
