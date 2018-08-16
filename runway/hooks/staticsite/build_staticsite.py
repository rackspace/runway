"""Stacker hook for building static website."""

import hashlib
import logging
import os
from subprocess import check_call
import tempfile
import zipfile

from boto3.s3.transfer import S3Transfer
import boto3
import six
import zgitignore

from botocore.exceptions import ClientError
from stacker.lookups.handlers.rxref import handler as rxref_handler
from stacker.session_cache import get_session

from ...util import change_dir

LOGGER = logging.getLogger(__name__)


def calculate_hash_of_files(files, root):
    """Return a hash of all of the given files at the given root.

    Args:
        files (list[str]): file names to include in the hash calculation,
            relative to ``root``.
        root (str): base directory to analyze files in.
    Returns:
        str: A hash of the hashes of the given files.

    """
    file_hash = hashlib.md5()
    for fname in sorted(files):
        fileobj = os.path.join(root, fname)
        file_hash.update((fname + "\0").encode())
        with open(fileobj, "rb") as filedes:
            for chunk in iter(lambda: filedes.read(4096), ""):  # noqa pylint: disable=cell-var-from-loop
                if not chunk:
                    break
                file_hash.update(chunk)
            file_hash.update("\0".encode())

    return file_hash.hexdigest()


def get_ignorer(path, additional_exclusions=None):
    """Create ignorer with directory gitignore file."""
    ignorefile = zgitignore.ZgitIgnore()
    gitignore_file = os.path.join(path, '.gitignore')
    if os.path.isfile(gitignore_file):
        with open(gitignore_file, 'r') as fileobj:
            ignorefile.add_patterns(fileobj.read().splitlines())

    if additional_exclusions is not None:
        ignorefile.add_patterns(additional_exclusions)

    return ignorefile


def get_hash_of_files(root_path, directories=None):
    """Generate md5 hash of files."""
    if not directories:
        directories = [{'path': './'}]

    files_to_hash = []
    for i in directories:
        ignorer = get_ignorer(os.path.join(root_path, i['path']),
                              i.get('exclusions'))

        with change_dir(root_path):
            for root, dirs, files in os.walk(i['path'], topdown=True):
                if (root != './') and ignorer.is_ignored(root, True):
                    dirs[:] = []
                    files[:] = []
                else:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if not ignorer.is_ignored(filepath):
                            files_to_hash.append(
                                filepath[2:] if filepath.startswith('./') else filepath  # noqa
                            )

    return calculate_hash_of_files(files_to_hash, root_path)


def run_commands(commands, directory):
    """Run list of commands."""
    # type: (List[Union[str, List[str], Dict[str, Union[str, List[str]]]]],
    #        str)
    # -> None
    for step in commands:
        if isinstance(step, (list, six.string_types)):
            execution_dir = directory
            raw_command = step
        elif step.get('command'):  # dictionary
            execution_dir = os.path.join(directory,
                                         step.get('cwd')) if step.get('cwd') else directory  # noqa pylint: disable=line-too-long
            raw_command = step['command']
        else:
            raise AttributeError("Invalid command step: %s" % step)
        command_list = raw_command.split(' ') if isinstance(raw_command, six.string_types) else raw_command  # noqa pylint: disable=line-too-long

        with change_dir(execution_dir):
            check_call(command_list, env=os.environ)


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
        else:
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
    artifact_key_prefix = "%s-%s-" % (options['namespace'], options['name'])
    default_param_name = "%shash" % artifact_key_prefix
    context_dict = {}

    if options.get('build_output'):
        build_output = os.path.join(
            options['path'],
            options['build_output']
        )
    else:
        build_output = options['path']

    artifact_bucket_name = rxref_handler(
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
    if options.get('source_hashing', {'enabled': True}).get('enabled', True):
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

    if old_parameter_value == context_dict['hash']:
        LOGGER.info("staticsite: skipping build; app hash %s already deployed "
                    "in this environment",
                    context_dict['hash'])
        context_dict['deploy_is_current'] = True
        return context_dict

    archive_key = artifact_key_prefix + context_dict['hash'] + '.zip'
    if does_s3_object_exist(artifact_bucket_name, archive_key, session):
        context_dict['app_directory'] = download_and_extract_to_mkdtemp(
            artifact_bucket_name, archive_key, session
        )
    else:
        if options.get('build_steps'):
            run_commands(options['build_steps'], options['path'])
        zip_and_upload(build_output, artifact_bucket_name, archive_key,
                       session)
        context_dict['app_directory'] = build_output

    context_dict['deploy_is_current'] = False
    return context_dict
