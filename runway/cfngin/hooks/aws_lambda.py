"""AWS Lambda hook."""
import hashlib
import logging
import os
import stat
import subprocess
import sys
# https://github.com/PyCQA/pylint/issues/2955
from distutils.util import strtobool  # pylint: disable=E
from io import BytesIO as StringIO
from shutil import copyfile
from types import GeneratorType
from zipfile import ZIP_DEFLATED, ZipFile

import botocore
import docker
import formic
from six import string_types
from troposphere.awslambda import Code

from ..exceptions import (InvalidDockerizePipConfiguration, PipenvError,
                          PipError)
from ..session_cache import get_session
from ..util import ensure_s3_bucket

if sys.version_info[0] < 3:
    from backports import tempfile  # pylint: disable=E
else:
    import tempfile

# mask to retrieve only UNIX file permissions from the external attributes
# field of a ZIP entry.
ZIP_PERMS_MASK = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) << 16

LOGGER = logging.getLogger(__name__)

# list from python tags of https://hub.docker.com/r/lambci/lambda/tags
SUPPORTED_RUNTIMES = [
    # Python 2.7 reached end-of-life on January 1st, 2020.
    # However, the Python 2.7 runtime is still supported and is not scheduled
    # to be deprecated at this time.
    # https://docs.aws.amazon.com/lambda/latest/dg/runtime-support-policy.html
    'python2.7',
    'python3.6',
    'python3.7',
    'python3.8'
]


def copydir(source, destination, includes, excludes=None,
            follow_symlinks=False):
    """Extend the functionality of shutil.

    Correctly copies files and directories in a source directory.

    Args:
        source (str): Source directory.
        destination (str): Destination directory.
        includes (List[str]): Glob patterns for files to include.
        includes (List[str]): Glob patterns for files to exclude.
        follow_symlinks (bool): If true, symlinks will be included in the
            resulting zip file.

    """
    files = _find_files(source, includes, excludes, follow_symlinks)

    def _mkdir(dir_name):
        """Recursively create directories."""
        parent = os.path.dirname(dir_name)
        if not os.path.isdir(parent):
            _mkdir(parent)
        LOGGER.debug('lambda.copydir: Creating directory: %s', dir_name)
        os.mkdir(dir_name)

    for file_name in files:
        src = os.path.join(source, file_name)
        dest = os.path.join(destination, file_name)
        try:
            LOGGER.debug('lambda.copydir: Copying file "%s" to "%s"',
                         src, dest)
            copyfile(src, dest)
        # python2 raises an IOError here
        except (IOError, OSError):
            _mkdir(os.path.dirname(dest))
            copyfile(src, dest)


def find_requirements(root):
    """Identify Python requirement files.

    Args:
        root (str): Path that should be searched for files.

    Returns:
        Optional[Dict[str, bool]]: Name of supported requirements file and
        wether it was found. If none are found, ``None`` is returned.

    """
    findings = {}

    for file_name in ['requirements.txt',
                      'Pipfile',
                      'Pipfile.lock']:
        findings[file_name] = os.path.isfile(os.path.join(root, file_name))

    if not sum(findings.values()):
        return None
    return findings


def should_use_docker(dockerize_pip=None):
    """Assess if Docker should be used based on the value of args.

    Args:
        dockerize_pip (Union[bool, None, str]): Value to assess if Docker
            should be used for pip.

    Returns:
        bool

    """
    if isinstance(dockerize_pip, bool):
        return dockerize_pip

    if isinstance(dockerize_pip, str):
        if dockerize_pip == 'non-linux' and \
                not sys.platform.startswith('linux'):
            return True
        try:
            return strtobool(dockerize_pip)
        except ValueError:
            pass
    return False


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
    if isinstance(files, GeneratorType):
        # if file list is a generator, save the contents so it can be reused
        # since generators are empty after the first iteration and cannot be
        # rewound.
        LOGGER.debug('lambda: Converting file generater to list for reuse...')
        files = list(files)
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


def _find_files(root, includes, excludes=None, follow_symlinks=False):
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


def handle_requirements(package_root, dest_path, requirements,
                        pipenv_timeout=300, python_path=None,
                        use_pipenv=False):
    """Use the correct requirements file.

    Args:
        package_root (str): Base directory containing a requirements file.
        dest_path (str): Where to output the requirements file if one needs
            to be created.
        requirements (Dict[str, bool]): Map of requirement file names and
            wether they exist.
        pipenv_timeout (int): Seconds to wait for a subprocess to complete.
        python_path (Optional[str]): Explicit python interpreter to be used.
            Requirement file generators must be installed and executable using
            ``-m`` if provided.
        use_pipenv (bool): Explicitly use pipenv to export a Pipfile as
            requirements.txt.

    Returns:
        str: Path to the final requirements.txt

    Raises:
        NotImplementedError: When a requirements file is not found. This
            should never be encountered but is included just in case.

    """
    if use_pipenv:
        LOGGER.info('lambda: explicitly using pipenv')
        return _handle_use_pipenv(package_root=package_root,
                                  dest_path=dest_path, python_path=python_path,
                                  timeout=pipenv_timeout)
    if requirements['requirements.txt']:
        LOGGER.info('lambda: using requirements.txt for dependencies')
        return os.path.join(dest_path, 'requirements.txt')
    if requirements['Pipfile'] or requirements['Pipfile.lock']:
        LOGGER.info('lambda: using pipenv for dependencies')
        return _handle_use_pipenv(package_root=package_root,
                                  dest_path=dest_path, python_path=python_path,
                                  timeout=pipenv_timeout)
    # This point should never be reached under normal operation since a
    # requirements file of some sort must have been found in another step
    # of the process but just in case it does happen, raise an error.
    raise NotImplementedError('Unable to handle missing requirements file.')


def _handle_use_pipenv(package_root, dest_path, python_path=None, timeout=300):
    """Create requirements file from Pipfile.

    Args:
        package_root (str): Base directory to generate requirements from.
        dest_path (str): Where to output the requirements file.
        python_path (Optional[str]): Explicit python interpreter to be used.
            pipenv must be installed and executable using ``-m`` if provided.
        timeout (int): Seconds to wait for process to complete.

    Raises:
        PipenvError: Non-zero exit code returned by pipenv process.

    """
    LOGGER.info('lambda.pipenv: Creating requirements.txt from Pipfile...')
    req_path = os.path.join(dest_path, 'requirements.txt')
    cmd = ['pipenv', 'lock', '--requirements', '--keep-outdated']
    if python_path:
        cmd.insert(0, python_path)
        cmd.insert(1, '-m')
    with open(req_path, 'w') as requirements:
        pipenv_process = subprocess.Popen(cmd, cwd=package_root,
                                          stdout=requirements,
                                          stderr=subprocess.PIPE)
        if int(sys.version[0]) > 2:
            # TODO remove pylint disable when dropping python2
            # pylint: disable=unexpected-keyword-arg
            _stdout, stderr = pipenv_process.communicate(timeout=timeout)
        else:
            _stdout, stderr = pipenv_process.communicate()
        if pipenv_process.returncode == 0:
            return req_path
        if int(sys.version[0]) > 2:
            stderr = stderr.decode('UTF-8')
        LOGGER.error('lambda.pipenv: "%s" failed with the following '
                     'output:\n%s', ' '.join(cmd), stderr)
        raise PipenvError


def dockerized_pip(work_dir, client=None, runtime=None, docker_file=None,
                   docker_image=None, **_kwargs):
    """Run pip with docker.

    Args:
        work_dir (str): Work directory for docker.
        client (Optional[docker.DockerClient]): Custom docker client.
        runtime (Optional[str]): Lambda runtime. Must provide one of
            ``runtime``, ``docker_file``, or ``docker_image``.
        docker_file (Optional[str]): Path to a Dockerfile to build an image.
            Must provide one of ``runtime``, ``docker_file``, or
            ``docker_image``.
        docker_image (Optional[str]): Local or remote docker image to use.
            Must provide one of ``runtime``, ``docker_file``, or
            ``docker_image``.
        kwargs (Any): Advanced options for docker. See source code to
            determine what is supported.

    Returns:
        Tuple[str, str]: Content of the ZIP file as a byte string and
        calculated hash of all the files

    """
    # TODO use kwargs to pass args to docker for advanced config
    if bool(docker_file) + bool(docker_image) + bool(runtime) != 1:
        # exactly one of these is needed. converting to bool will give us a
        # 'False' (0) for 'None' and 'True' (1) for anything else.
        raise InvalidDockerizePipConfiguration(
            'exactly only one of [docker_file, docker_file, runtime] must be '
            'provided'
        )

    if not client:
        client = docker.from_env()

    if docker_file:
        if not os.path.isfile(docker_file):
            raise ValueError('could not find docker_file "%s"' % docker_file)
        LOGGER.info('lambda.docker: Building docker image from "%s".',
                    docker_file)
        response = client.images.build(
            path=os.path.dirname(docker_file),
            dockerfile=os.path.basename(docker_file),
            forcerm=True
        )
        # the response can be either a tuple of (Image, Generator[Dict[str, str]])
        # or just Image depending on API version.
        if isinstance(response, tuple):
            docker_image = response[0].id
            for log_msg in response[1]:
                if log_msg.get('stream'):
                    LOGGER.info(log_msg['stream'].strip('\n'))
        else:
            docker_image = response.id
        LOGGER.info('lambda.docker: Docker image "%s" created.', docker_image)
    if runtime:
        if runtime not in SUPPORTED_RUNTIMES:
            raise ValueError('invalid runtime "{}" must be one of {}'.format(
                runtime, str(SUPPORTED_RUNTIMES)
            ))
        docker_image = 'lambci/lambda:build-%s' % runtime
        LOGGER.debug('lambda.docker: Selected docker image "%s" based on '
                     'provided runtime', docker_image)

    if sys.platform.lower() == 'win32':
        LOGGER.debug('lambda.docker: Formatted docker mount path for Windows')
        work_dir = work_dir.replace('\\', '/')

    work_dir_mount = docker.types.Mount(target='/var/task',
                                        source=work_dir,
                                        type='bind')
    pip_cmd = (
        'python -m pip install -t /var/task -r /var/task/requirements.txt'
    )

    LOGGER.info('lambda.docker: Using docker image "%s" to build deployment '
                'package...', docker_image)

    container = client.containers.run(image=docker_image,
                                      command=['/bin/sh', '-c', pip_cmd],
                                      auto_remove=True,
                                      detach=True,
                                      mounts=[work_dir_mount])

    # 'stream' creates a blocking generator that allows for real-time logs.
    # this loop ends when the container 'auto_remove's itself.
    for log in container.logs(stdout=True,
                              stderr=True,
                              stream=True,
                              tail=0):
        # without strip there are a bunch blank lines in the output
        LOGGER.info('lambda.docker: %s', log.decode().strip())


def _zip_package(package_root, includes, excludes=None, dockerize_pip=False,
                 follow_symlinks=False, python_path=None,
                 requirements_files=None, use_pipenv=False, **kwargs):
    """Create zip file in memory with package dependencies.

    Args:
        package_root (str): Base directory to copy files from.
        includes (List[str]): Inclusion patterns. Only files  matching those
            patterns will be included in the result.
        excludes (List[str]): Exclusion patterns. Files matching those
            patterns will be excluded from the result. Exclusions take
            precedence over inclusions.
        dockerize_pip (Union[bool, str]): Whether to use docker or under what
            conditions docker will be used to run ``pip``.
        follow_symlinks (bool): If true, symlinks will be included in the
            resulting zip file.
        python_path (Optional[str]): Explicit python interpreter to be used.
            pipenv must be installed and executable using ``-m`` if provided.
        requirements_files (Dict[str, bool]): Map of requirement file names and
            wether they exist.
        use_pipenv (bool): Wether to use pipenv to export a Pipfile as
            requirements.txt.
        kwargs (Any): Advanced options for subprocess and docker. See source
            code to determine what is supported.

    Returns:
        Tuple[str, str]: Content of the ZIP file as a byte string and
        calculated hash of all the files

    """
    kwargs.setdefault('pipenv_timeout', 300)

    temp_root = os.path.join(os.path.expanduser('~'), '.runway_cache')
    if not os.path.isdir(temp_root):
        os.makedirs(temp_root)

    # exclude potential virtual environments in the package
    excludes.append('.venv/')

    # TODO remove pylint disable when dropping python2
    with tempfile.TemporaryDirectory(
            prefix='cfngin', dir=temp_root  # pylint: disable=bad-continuation
    ) as tmpdir:
        tmp_req = os.path.join(tmpdir, 'requirements.txt')
        copydir(package_root, tmpdir, includes, excludes, follow_symlinks)
        tmp_req = handle_requirements(package_root=package_root,
                                      dest_path=tmpdir,
                                      requirements=requirements_files,
                                      python_path=python_path,
                                      use_pipenv=use_pipenv,
                                      pipenv_timeout=kwargs['pipenv_timeout'])

        if should_use_docker(dockerize_pip):
            dockerized_pip(tmpdir, **kwargs)
        else:
            pip_cmd = [python_path or sys.executable, '-m',
                       'pip', 'install',
                       '-t', tmpdir,
                       '-r', tmp_req]
            pip_proc = subprocess.Popen(pip_cmd,
                                        cwd=tmpdir, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
            if int(sys.version[0]) > 2:
                # TODO remove pylint disable when dropping python2
                # pylint: disable=unexpected-keyword-arg
                _stdout, stderr = pip_proc.communicate(timeout=kwargs.get(
                    'pipenv_timeout', 900
                ))
            else:
                _stdout, stderr = pip_proc.communicate()
            if pip_proc.returncode != 0:
                if int(sys.version[0]) > 2:
                    stderr = stderr.decode('UTF-8')
                LOGGER.error('"%s" failed with the following output:\n%s',
                             ' '.join(pip_cmd), stderr)
                raise PipError

        req_files = _find_files(tmpdir, includes='**', follow_symlinks=False)
        return _zip_files(req_files, tmpdir)


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
                     payload_acl, sys_path):
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
        sys_path (str): Path that all actions are relative to.

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
        root = os.path.abspath(os.path.join(sys_path, root))
    requirements_files = find_requirements(root)
    if requirements_files:
        zip_contents, content_hash = _zip_package(
            root,
            includes=includes,
            excludes=excludes,
            follow_symlinks=follow_symlinks,
            requirements_files=requirements_files,
            **options
        )
    else:
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

            **docker_file (Optional[str])**
                Path to a local DockerFile that will be built and used for
                ``dockerize_pip``. Must provide exactly one of ``docker_file``,
                ``docker_image``, or ``runtime``.

            **docker_image (Optional[str])**
                Custom Docker image to use  with ``dockerize_pip``. Must
                provide exactly one of ``docker_file``, ``docker_image``, or
                ``runtime``.

            **dockerize_pip (Optional[Union[str, bool]])**
                Whether to use Docker when preparing package dependencies with
                pip. Can be set to True/False or the special string 'non-linux'
                which will only run on non Linux systems. To use this option
                Docker must be installed.

            **exclude (Optional[Union[str, List[str]]])**
                Pattern or list of patterns of files to exclude from the
                payload. If provided, any files that match will be ignored,
                regardless of whether they match an inclusion pattern.

                Commonly ignored files are already excluded by default,
                such as ``.git``, ``.svn``, ``__pycache__``, ``*.pyc``,
                ``.gitignore``, etc.

            **include (Optional[Union[str, List[str]]])**
                Pattern or list of patterns of files to include in the
                payload. If provided, only files that match these
                patterns will be included in the payload.

                Omitting it is equivalent to accepting all files that are
                not otherwise excluded.

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

            **pipenv_lock_timeout (Optional[int])**
                Time in seconds to wait while creating lock file with pipenv.

            **pipenv_timeout (Optional[int])**
                Time in seconds to wait while running pipenv.

            **python_path (Optional[str])**
                Absolute path to a python interpreter to use for
                ``pip``/``pipenv`` actions. If not provided, the current
                python interpreter will be used for ``pip`` and ``pipenv``
                will be used from the current ``$PATH``.

            **runtime (Optional[str])**
                Runtime of the AWS Lambda Function being uploaded. Used with
                ``dockerize_pip`` to automatically select the appropriate
                Docker image to use. Must provide exactly one of
                ``docker_file``, ``docker_image``, or ``runtime``.

            **use_pipenv (Optional[bool])**
                Explicitly use Pipfile/Pipfile.lock to prepare package
                dependencies even if a requirements.txt file is found.

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
                      dockerize_pip: non-linux
                      use_pipenv: true
                      runtime: python3.8
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
    # TODO add better handling for misconfiguration (e.g. forgetting function names)
    # TODO support defining dockerize_pip options at the top level of args
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
        sys_path = (os.path.dirname(context.config_path)
                    if os.path.isfile(context.config_path)
                    else context.config_path)
        results[name] = _upload_function(s3_client, bucket_name, prefix, name,
                                         options, follow_symlinks, payload_acl,
                                         sys_path)

    return results
