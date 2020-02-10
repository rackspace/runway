"""AWS Lambda hook."""
import hashlib
import logging
import os
import os.path
import stat
from io import BytesIO as StringIO
from zipfile import ZIP_DEFLATED, ZipFile

import botocore
import formic
from six import string_types
from troposphere.awslambda import Code

from ..session_cache import get_session
from ..util import ensure_s3_bucket, get_config_directory

# mask to retrieve only UNIX file permissions from the external attributes
# field of a ZIP entry.
ZIP_PERMS_MASK = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) << 16

LOGGER = logging.getLogger(__name__)


def _zip_files(files, root):
    """Generate a ZIP file in-memory from a list of files.

    Files will be stored in the archive with relative names, and have their
    UNIX permissions forced to 755 or 644 (depending on whether they are
    user-executable in the source filesystem).

    Args:
        files (List[str]): file names to add to the archive, relative to
            ``root``.
        root (str): base directory to retrieve files from.

    Returns:
        Tuple[str, str]: Content of the ZIP file as a byte string and
        calculated hash of all the files

    """
    zip_data = StringIO()
    with ZipFile(zip_data, 'w', ZIP_DEFLATED) as zip_file:
        for file_name in files:
            zip_file.write(os.path.join(root, file_name), file_name)

        # Fix file permissions to avoid any issues - only care whether a file
        # is executable or not, choosing between modes 755 and 644 accordingly.
        for zip_entry in zip_file.filelist:
            perms = (zip_entry.external_attr & ZIP_PERMS_MASK) >> 16
            if perms & stat.S_IXUSR != 0:
                new_perms = 0o755
            else:
                new_perms = 0o644

            if new_perms != perms:
                LOGGER.debug("lambda: fixing perms: %s: %o => %o",
                             zip_entry.filename, perms, new_perms)
                new_attr = (
                    (zip_entry.external_attr & ~ZIP_PERMS_MASK) | (new_perms << 16)
                )
                zip_entry.external_attr = new_attr

    contents = zip_data.getvalue()
    zip_data.close()
    content_hash = _calculate_hash(files, root)

    return contents, content_hash


def _calculate_hash(files, root):
    """Return a hash of all of the given files at the given root.

    Args:
        files (list[str]): file names to include in the hash calculation,
            relative to ``root``.
        root (str): base directory to analyze files in.

    Returns:
        str: A hash of the hashes of the given files.

    """
    file_hash = hashlib.md5()
    for file_name in sorted(files):
        file_path = os.path.join(root, file_name)
        file_hash.update((file_name + "\0").encode())
        with open(file_path, "rb") as file_:
            for chunk in iter(lambda: file_.read(4096), ""):  # pylint: disable=W
                if not chunk:
                    break
                file_hash.update(chunk)
            file_hash.update("\0".encode())

    return file_hash.hexdigest()


def _find_files(root, includes, excludes, follow_symlinks):
    """List files inside a directory based on include and exclude rules.

    This is a more advanced version of `glob.glob`, that accepts multiple
    complex patterns.

    Args:
        root (str): base directory to list files from.
        includes (List[str]): inclusion patterns. Only files matching those
            patterns will be included in the result.
        excludes (List[str]): exclusion patterns. Files matching those
            patterns will be excluded from the result. Exclusions take
            precedence over inclusions.
        follow_symlinks (bool): If true, symlinks will be included in the
            resulting zip file

    Yields:
        str: a file name relative to the root.

    Note:
        Documentation for the patterns can be found at
        http://www.aviser.asia/formic/doc/index.html

    """
    root = os.path.abspath(root)
    file_set = formic.FileSet(
        directory=root, include=includes,
        exclude=excludes, symlinks=follow_symlinks,
    )

    for filename in file_set.qualified_files(absolute=False):
        yield filename


def _zip_from_file_patterns(root, includes, excludes, follow_symlinks):
    """Generate a ZIP file in-memory from file search patterns.

    Args:
        root (str): Base directory to list files from.
        includes (List[str]): Inclusion patterns. Only files  matching those
            patterns will be included in the result.
        excludes (List[str]): Exclusion patterns. Files matching those
            patterns will be excluded from the result. Exclusions take
            precedence over inclusions.
        follow_symlinks (bool): If true, symlinks will be included in the
            resulting zip file

    See Also:
        :func:`_zip_files`, :func:`_find_files`.

    Raises:
        RuntimeError: when the generated archive would be empty.

    """
    LOGGER.info('lambda: base directory: %s', root)

    files = list(_find_files(root, includes, excludes, follow_symlinks))
    if not files:
        raise RuntimeError('Empty list of files for Lambda payload. Check '
                           'your include/exclude options for errors.')

    LOGGER.info('lambda: adding %d files:', len(files))

    for file_name in files:
        LOGGER.debug('lambda: + %s', file_name)

    return _zip_files(files, root)


def _head_object(s3_conn, bucket, key):
    """Retrieve information about an object in S3 if it exists.

    Args:
        s3_conn (botocore.client.S3): S3 connection to use for operations.
        bucket (str): name of the bucket containing the key.
        key (str): name of the key to lookup.

    Returns:
        Dict[str, Any]: S3 object information, or None if the object does not
        exist. See the AWS documentation for explanation of the contents.

    Raises:
        botocore.exceptions.ClientError: any error from boto3 other than key
            not found is passed through.

    """
    try:
        return s3_conn.head_object(Bucket=bucket, Key=key)
    except botocore.exceptions.ClientError as err:
        if err.response['Error']['Code'] == '404':
            return None
        raise


def _upload_code(s3_conn, bucket, prefix, name, contents, content_hash,
                 payload_acl):
    """Upload a ZIP file to S3 for use by Lambda.

    The key used for the upload will be unique based on the checksum of the
    contents. No changes will be made if the contents in S3 already match the
    expected contents.

    Args:
        s3_conn (botocore.client.S3): S3 connection to use for operations.
        bucket (str): name of the bucket to create.
        prefix (str): S3 prefix to prepend to the constructed key name for
            the uploaded file
        name (str): desired name of the Lambda function. Will be used to
            construct a key name for the uploaded file.
        contents (str): byte string with the content of the file upload.
        content_hash (str): md5 hash of the contents to be uploaded.
        payload_acl (str): The canned S3 object ACL to be applied to the
            uploaded payload

    Returns:
        troposphere.awslambda.Code: CloudFormation Lambda Code object,
        pointing to the uploaded payload in S3.

    Raises:
        botocore.exceptions.ClientError: any error from boto3 is passed
            through.

    """
    LOGGER.debug('lambda: ZIP hash: %s', content_hash)
    key = '{}lambda-{}-{}.zip'.format(prefix, name, content_hash)

    if _head_object(s3_conn, bucket, key):
        LOGGER.info('lambda: object %s already exists, not uploading', key)
    else:
        LOGGER.info('lambda: uploading object %s', key)
        s3_conn.put_object(Bucket=bucket, Key=key, Body=contents,
                           ContentType='application/zip',
                           ACL=payload_acl)

    return Code(S3Bucket=bucket, S3Key=key)


def _check_pattern_list(patterns, key, default=None):
    """Validate file search patterns from user configuration.

    Acceptable input is a string (which will be converted to a singleton list),
    a list of strings, or anything falsy (such as None or an empty dictionary).
    Empty or unset input will be converted to a default.

    Args:
        patterns: Input from user configuration (YAML).
        key (str): Name of the configuration key the input came from,
            used for error display purposes.

    Keyword Args:
        default: Value to return in case the input is empty or unset.

    Returns:
        List[str]: Validated list of patterns.

    Raises:
        ValueError: If the input is unacceptable.

    """
    if not patterns:
        return default

    if isinstance(patterns, string_types):
        return [patterns]

    if isinstance(patterns, list):
        if all(isinstance(p, string_types) for p in patterns):
            return patterns

    raise ValueError("Invalid file patterns in key '{}': must be a string or "
                     'list of strings'.format(key))


def _upload_function(s3_conn, bucket, prefix, name, options, follow_symlinks,
                     payload_acl):
    """Build a Lambda payload from user configuration and uploads it to S3.

    Args:
        s3_conn (botocore.client.S3): S3 connection to use for operations.
        bucket (str): name of the bucket to upload to.
        prefix (str): S3 prefix to prepend to the constructed key name for
            the uploaded file
        name (str): Desired name of the Lambda function. Will be used to
            construct a key name for the uploaded file.
        options (Dict[str, Any]): Configuration for how to build the payload.
            Consists of the following keys:
                **path**:
                    Base path to retrieve files from (mandatory). If not
                    absolute, it will be interpreted as relative to the CFNgin
                    configuration file directory, then converted to an absolute
                    path. See :func:`runway.cfngin.util.get_config_directory`.
                **include**:
                    File patterns to include in the payload (optional).
                **exclude**:
                    File patterns to exclude from the payload (optional).
        follow_symlinks (bool): If true, symlinks will be included in the
            resulting zip file
        payload_acl (str): The canned S3 object ACL to be applied to the
            uploaded payload

    Returns:
        troposphere.awslambda.Code: CloudFormation AWS Lambda Code object,
        pointing to the uploaded object in S3.

    Raises:
        ValueError: If any configuration is invalid.
        botocore.exceptions.ClientError: Any error from boto3 is passed
            through.

    """
    try:
        root = os.path.expanduser(options['path'])
    except KeyError as err:
        raise ValueError(
            "missing required property '{}' in function '{}'".format(
                err.args[0], name))

    includes = _check_pattern_list(options.get('include'), 'include',
                                   default=['**'])
    excludes = _check_pattern_list(options.get('exclude'), 'exclude',
                                   default=[])

    LOGGER.debug('lambda: processing function %s', name)

    # os.path.join will ignore other parameters if the right-most one is an
    # absolute path, which is exactly what we want.
    if not os.path.isabs(root):
        root = os.path.abspath(os.path.join(get_config_directory(), root))
    zip_contents, content_hash = _zip_from_file_patterns(root,
                                                         includes,
                                                         excludes,
                                                         follow_symlinks)

    return _upload_code(s3_conn, bucket, prefix, name, zip_contents,
                        content_hash, payload_acl)


def select_bucket_region(custom_bucket, hook_region, cfngin_bucket_region,
                         provider_region):
    """Return the appropriate region to use when uploading functions.

    Select the appropriate region for the bucket where lambdas are uploaded in.

    Args:
        custom_bucket (Optional[str]): The custom bucket name provided by the
            `bucket` kwarg of the aws_lambda hook, if provided.
        hook_region (str): The contents of the `bucket_region` argument to
            the hook.
        cfngin_bucket_region (str): The contents of the
            ``cfngin_bucket_region`` global setting.
        provider_region (str): The region being used by the provider.

    Returns:
        str: The appropriate region string.

    """
    region = None
    if custom_bucket:
        region = hook_region
    else:
        region = cfngin_bucket_region
    return region or provider_region


def upload_lambda_functions(context, provider, **kwargs):
    """Build Lambda payloads from user configuration and upload them to S3.

    Constructs ZIP archives containing files matching specified patterns for
    each function, uploads the result to Amazon S3, then stores objects (of
    type :class:`troposphere.awslambda.Code`) in the context's hook data,
    ready to be referenced in blueprints.

    Configuration consists of some global options, and a dictionary of function
    specifications. In the specifications, each key indicating the name of the
    function (used for generating names for artifacts), and the value
    determines what files to include in the ZIP (see more details below).

    Payloads are uploaded to either a custom bucket or the CFNgin default
    bucket, with the key containing it's checksum, to allow repeated uploads
    to be skipped in subsequent runs.

    The configuration settings are documented as keyword arguments below.

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance. (passed in by CFNgin)
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        bucket (Optional[str]): Custom bucket to upload functions to.
            Omitting it will cause the default CFNgin bucket to be used.
        bucket_region (Optional[str]): The region in which the bucket should
            exist. If not given, the region will be either be that of the
            global ``cfngin_bucket_region`` setting, or else the region in
            use by the provider.
        prefix (Optional[str]): S3 key prefix to prepend to the uploaded
            zip name.
        follow_symlinks (Optional[bool]): Will determine if symlinks should
            be followed and included with the zip artifact. (*default:*
            ``False``)
        payload_acl (Optional[str]): The canned S3 object ACL to be applied
            to the uploaded payload. (*default: private*)
        functions (Dict[str, Any]): Configurations of desired payloads to
            build. Keys correspond to function names, used to derive key
            names for the payload. Each value should itself be a dictionary,
            with the following data:

            **path (str)**
                Base directory of the Lambda function payload content.
                If it not an absolute path, it will be considered relative
                to the directory containing the CFNgin configuration file
                in use.

                Files in this directory will be added to the payload ZIP,
                according to the include and exclude patterns. If not
                patterns are provided, all files in this directory
                (respecting default exclusions) will be used.

                Files are stored in the archive with path names relative to
                this directory. So, for example, all the files contained
                directly under this directory will be added to the root of
                the ZIP file.

            **include (Optional[Union[str, List[str]]])**
                Pattern or list of patterns of files to include in the
                payload. If provided, only files that match these
                patterns will be included in the payload.

                Omitting it is equivalent to accepting all files that are
                not otherwise excluded.

            **exclude (Optional[Union[str, List[str]]])**
                Pattern or list of patterns of files to exclude from the
                payload. If provided, any files that match will be ignored,
                regardless of whether they match an inclusion pattern.

                Commonly ignored files are already excluded by default,
                such as ``.git``, ``.svn``, ``__pycache__``, ``*.pyc``,
                ``.gitignore``, etc.

    Examples:
        .. Hook configuration.
        .. code-block:: yaml

            pre_build:
              upload_functions:
                path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
                required: true
                enabled: true
                data_key: lambda
                args:
                  bucket: custom-bucket
                  follow_symlinks: true
                  prefix: cloudformation-custom-resources/
                  payload_acl: authenticated-read
                  functions:
                    MyFunction:
                      path: ./lambda_functions
                      include:
                        - '*.py'
                        - '*.txt'
                      exclude:
                        - '*.pyc'
                        - test/

        .. Blueprint usage
        .. code-block:: python

            from troposphere.awslambda import Function
            from runway.cfngin.blueprints.base import Blueprint

            class LambdaBlueprint(Blueprint):
                def create_template(self):
                    code = self.context.hook_data['lambda']['MyFunction']

                    self.template.add_resource(
                        Function(
                            'MyFunction',
                            Code=code,
                            Handler='my_function.handler',
                            Role='...',
                            Runtime='python2.7'
                        )
                    )

    """
    custom_bucket = kwargs.get('bucket')
    if not custom_bucket:
        bucket_name = context.bucket_name
        LOGGER.info("lambda: using default bucket from CFNgin: %s",
                    bucket_name)
    else:
        bucket_name = custom_bucket
        LOGGER.info("lambda: using custom bucket: %s", bucket_name)

    custom_bucket_region = kwargs.get("bucket_region")
    if not custom_bucket and custom_bucket_region:
        raise ValueError("Cannot specify `bucket_region` without specifying "
                         "`bucket`.")

    bucket_region = select_bucket_region(
        custom_bucket,
        custom_bucket_region,
        context.config.cfngin_bucket_region,
        provider.region
    )

    # Check if we should walk / follow symlinks
    follow_symlinks = kwargs.get('follow_symlinks', False)
    if not isinstance(follow_symlinks, bool):
        raise ValueError('follow_symlinks option must be a boolean')

    # Check for S3 object acl. Valid values from:
    # https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
    payload_acl = kwargs.get('payload_acl', 'private')

    # Always use the global client for s3
    session = get_session(bucket_region)
    s3_client = session.client('s3')

    ensure_s3_bucket(s3_client, bucket_name, bucket_region)

    prefix = kwargs.get('prefix', '')

    results = {}
    for name, options in kwargs['functions'].items():
        results[name] = _upload_function(s3_client, bucket_name, prefix, name,
                                         options, follow_symlinks, payload_acl)

    return results
