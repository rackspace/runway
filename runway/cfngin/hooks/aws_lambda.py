"""AWS Lambda hook."""
# pylint: disable=too-many-lines
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from distutils.util import strtobool
from io import BytesIO as StringIO
from pathlib import Path
from shutil import copyfile
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)
from zipfile import ZIP_DEFLATED, ZipFile

import botocore
import botocore.exceptions
import docker
import docker.types
import formic
from docker.models.containers import Container
from docker.models.images import Image
from troposphere.awslambda import Code
from typing_extensions import Literal, TypedDict

from ...constants import DOT_RUNWAY_DIR
from ..exceptions import InvalidDockerizePipConfiguration, PipenvError, PipError
from ..utils import ensure_s3_bucket

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef

    from ...context import CfnginContext
    from ..providers.aws.default import Provider

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
    "python2.7",
    "python3.6",
    "python3.7",
    "python3.8",
]

DockerizePipArgTypeDef = Optional[
    Union[
        bool,
        Literal[
            "false", "False", "no", "No", "non-linux", "true", "True", "yes", "Yes"
        ],
    ]
]
PayloadAclTypeDef = Optional[
    Literal[
        "authenticated-read",
        "aws-exec-read",
        "bucket-owner-full-control",
        "bucket-owner-read",
        "private",
        "public-read-write",
        "public-read",
    ]
]


def copydir(
    source: str,
    destination: str,
    includes: List[str],
    excludes: Optional[List[str]] = None,
    follow_symlinks: bool = False,
) -> None:
    """Extend the functionality of shutil.

    Correctly copies files and directories in a source directory.

    Args:
        source: Source directory.
        destination: Destination directory.
        includes: Glob patterns for files to include.
        excludes: Glob patterns for files to exclude.
        follow_symlinks: If true, symlinks will be included in the resulting zip
            file.

    """
    files = _find_files(source, includes, excludes, follow_symlinks)

    def _mkdir(dir_name: str) -> None:
        """Recursively create directories."""
        parent = os.path.dirname(dir_name)
        if not os.path.isdir(parent):
            _mkdir(parent)
        LOGGER.debug("creating directory: %s", dir_name)
        os.mkdir(dir_name)

    for file_name in files:
        src = os.path.join(source, file_name)
        dest = os.path.join(destination, file_name)
        try:
            LOGGER.debug('copying file "%s" to "%s"', src, dest)
            copyfile(src, dest)
        except OSError:
            _mkdir(os.path.dirname(dest))
            copyfile(src, dest)


def find_requirements(root: str) -> Optional[Dict[str, bool]]:
    """Identify Python requirement files.

    Args:
        root: Path that should be searched for files.

    Returns:
        Name of supported requirements file and whether it was found.
        If none are found, ``None`` is returned.

    """
    findings = {
        file_name: os.path.isfile(os.path.join(root, file_name))
        for file_name in ["requirements.txt", "Pipfile", "Pipfile.lock"]
    }

    if not sum(findings.values()):
        return None
    return findings


def should_use_docker(dockerize_pip: DockerizePipArgTypeDef = None) -> bool:
    """Assess if Docker should be used based on the value of args.

    Args:
        dockerize_pip: Value to assess if Docker should be used for pip.

    """
    if isinstance(dockerize_pip, bool):
        return dockerize_pip

    if isinstance(dockerize_pip, str):
        if dockerize_pip == "non-linux" and not sys.platform.startswith("linux"):
            return True
        try:
            return strtobool(dockerize_pip)
        except ValueError:
            pass
    return False


def _zip_files(files: Iterable[str], root: str) -> Tuple[bytes, str]:
    """Generate a ZIP file in-memory from a list of files.

    Files will be stored in the archive with relative names, and have their
    UNIX permissions forced to 755 or 644 (depending on whether they are
    user-executable in the source filesystem).

    Args:
        files: file names to add to the archive, relative to ``root``.
        root: base directory to retrieve files from.

    Returns:
        Content of the ZIP file as a byte string and calculated hash of all the files.

    """
    zip_data = StringIO()
    files = list(files)  # create copy of list also converts generator to list
    with ZipFile(zip_data, "w", ZIP_DEFLATED) as zip_file:
        for file_name in files:
            zip_file.write(os.path.join(root, file_name), file_name)

        # Fix file permissions to avoid any issues - only care whether a file
        # is executable or not, choosing between modes 755 and 644 accordingly.
        for zip_entry in zip_file.filelist:
            perms = (zip_entry.external_attr & ZIP_PERMS_MASK) >> 16
            new_perms = 0o755 if perms & stat.S_IXUSR != 0 else 0o644
            if new_perms != perms:
                LOGGER.debug(
                    "fixing perms: %s: %o => %o", zip_entry.filename, perms, new_perms
                )
                new_attr = (zip_entry.external_attr & ~ZIP_PERMS_MASK) | (
                    new_perms << 16
                )
                zip_entry.external_attr = new_attr

    contents = zip_data.getvalue()
    zip_data.close()
    content_hash = _calculate_hash(files, root)

    return contents, content_hash


def _calculate_hash(files: Iterable[str], root: str) -> str:
    """Return a hash of all of the given files at the given root.

    Args:
        files: file names to include in the hash calculation,
            relative to ``root``.
        root: base directory to analyze files in.

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


def _find_files(
    root: str,
    includes: Union[List[str], str],
    excludes: Optional[List[str]] = None,
    follow_symlinks: bool = False,
) -> Iterator[str]:
    """List files inside a directory based on include and exclude rules.

    This is a more advanced version of `glob.glob`, that accepts multiple
    complex patterns.

    Args:
        root: base directory to list files from.
        includes: inclusion patterns. Only files matching those patterns will be
            included in the result.
        excludes: exclusion patterns. Files matching those patterns will be
            excluded from the result. Exclusions take precedence over inclusions.
        follow_symlinks: If true, symlinks will be included in the resulting zip file.

    Yields:
        File names relative to the root.

    Note:
        Documentation for the patterns can be found at
        http://www.aviser.asia/formic/doc/index.html

    """
    root = os.path.abspath(root)
    file_set = formic.FileSet(
        directory=root, include=includes, exclude=excludes, symlinks=follow_symlinks
    )
    yield from file_set.qualified_files(absolute=False)


def _zip_from_file_patterns(
    root: str, includes: List[str], excludes: List[str], follow_symlinks: bool
) -> Tuple[bytes, str]:
    """Generate a ZIP file in-memory from file search patterns.

    Args:
        root: Base directory to list files from.
        includes: Inclusion patterns. Only files  matching those patterns will be
            included in the result.
        excludes: Exclusion patterns. Files matching those patterns will be
            excluded from the result. Exclusions take precedence over inclusions.
        follow_symlinks: If true, symlinks will be included in the resulting zip file.

    See Also:
        :func:`_zip_files`, :func:`_find_files`.

    Raises:
        RuntimeError: when the generated archive would be empty.

    """
    LOGGER.info("base directory: %s", root)

    files = list(_find_files(root, includes, excludes, follow_symlinks))
    if not files:
        raise RuntimeError(
            "Empty list of files for Lambda payload. Check "
            "your include/exclude options for errors."
        )

    LOGGER.info("adding %d files:", len(files))

    for file_name in files:
        LOGGER.debug(" + %s", file_name)

    return _zip_files(files, root)


def handle_requirements(
    package_root: str,
    dest_path: str,
    requirements: Dict[str, bool],
    pipenv_timeout: int = 300,
    python_path: Optional[str] = None,
    use_pipenv: bool = False,
) -> str:
    """Use the correct requirements file.

    Args:
        package_root: Base directory containing a requirements file.
        dest_path: Where to output the requirements file if one needs to be created.
        requirements: Map of requirement file names and whether they exist.
        pipenv_timeout: Seconds to wait for a subprocess to complete.
        python_path: Explicit python interpreter to be used. Requirement file
            generators must be installed and executable using ``-m`` if provided.
        use_pipenv: Explicitly use pipenv to export a Pipfile as requirements.txt.

    Returns:
        Path to the final requirements.txt

    Raises:
        NotImplementedError: When a requirements file is not found. This
            should never be encountered but is included just in case.

    """
    if use_pipenv:
        LOGGER.info("explicitly using pipenv")
        return _handle_use_pipenv(
            package_root=package_root,
            dest_path=dest_path,
            python_path=python_path,
            timeout=pipenv_timeout,
        )
    if requirements["requirements.txt"]:
        LOGGER.info("using requirements.txt for dependencies")
        return os.path.join(dest_path, "requirements.txt")
    if requirements["Pipfile"] or requirements["Pipfile.lock"]:
        LOGGER.info("using pipenv for dependencies")
        return _handle_use_pipenv(
            package_root=package_root,
            dest_path=dest_path,
            python_path=python_path,
            timeout=pipenv_timeout,
        )
    # This point should never be reached under normal operation since a
    # requirements file of some sort must have been found in another step
    # of the process but just in case it does happen, raise an error.
    raise NotImplementedError("Unable to handle missing requirements file.")


def _handle_use_pipenv(
    package_root: str,
    dest_path: str,
    python_path: Optional[str] = None,
    timeout: int = 300,
) -> str:
    """Create requirements file from Pipfile.

    Args:
        package_root: Base directory to generate requirements from.
        dest_path: Where to output the requirements file.
        python_path: Explicit python interpreter to be used. pipenv must be
            installed and executable using ``-m`` if provided.
        timeout: Seconds to wait for process to complete.

    Raises:
        PipenvError: Non-zero exit code returned by pipenv process.

    """
    if getattr(sys, "frozen", False):
        LOGGER.error("pipenv can only be used with python installed from PyPi")
        sys.exit(1)
    LOGGER.info("creating requirements.txt from Pipfile...")
    req_path = os.path.join(dest_path, "requirements.txt")
    cmd = ["pipenv", "lock", "--requirements", "--keep-outdated"]
    if python_path:
        cmd.insert(0, python_path)
        cmd.insert(1, "-m")
    with open(req_path, "w", encoding="utf-8") as requirements:
        with subprocess.Popen(
            cmd, cwd=package_root, stdout=requirements, stderr=subprocess.PIPE
        ) as pipenv_process:
            if int(sys.version[0]) > 2:
                _stdout, stderr = pipenv_process.communicate(timeout=timeout)
            else:
                _stdout, stderr = pipenv_process.communicate()
            if pipenv_process.returncode == 0:
                return req_path
            if int(sys.version[0]) > 2:
                stderr = stderr.decode("UTF-8")
            LOGGER.error(
                '"%s" failed with the following output:\n%s', " ".join(cmd), stderr
            )
            raise PipenvError


def dockerized_pip(
    work_dir: str,
    client: Optional[docker.DockerClient] = None,
    runtime: Optional[str] = None,
    docker_file: Optional[str] = None,
    docker_image: Optional[str] = None,
    python_dontwritebytecode: bool = False,
    **_: Any,
) -> None:
    """Run pip with docker.

    Args:
        work_dir: Work directory for docker.
        client: Custom docker client.
        runtime: Lambda runtime. Must provide one of ``runtime``,
            ``docker_file``, or ``docker_image``.
        docker_file: Path to a Dockerfile to build an image.
            Must provide one of ``runtime``, ``docker_file``, or ``docker_image``.
        docker_image: Local or remote docker image to use.
            Must provide one of ``runtime``, ``docker_file``, or ``docker_image``.
        python_dontwritebytecode: Don't write bytecode.

    """
    # TODO use kwargs to pass args to docker for advanced config
    if bool(docker_file) + bool(docker_image) + bool(runtime) != 1:
        # exactly one of these is needed. converting to bool will give us a
        # 'False' (0) for 'None' and 'True' (1) for anything else.
        raise InvalidDockerizePipConfiguration(
            "exactly only one of [docker_file, docker_file, runtime] must be "
            "provided"
        )

    if not client:
        client = docker.from_env()

    if docker_file:
        if not os.path.isfile(docker_file):
            raise ValueError(f'could not find docker_file "{docker_file}"')
        LOGGER.info('building docker image from "%s"', docker_file)
        response = cast(
            Union[Image, Tuple[Image, Iterator[Dict[str, str]]]],
            client.images.build(
                path=os.path.dirname(docker_file),
                dockerfile=os.path.basename(docker_file),
                forcerm=True,
            ),
        )
        # the response can be either a tuple of (Image, Generator[Dict[str, str]])
        # or just Image depending on API version.
        if isinstance(response, tuple):
            docker_image = cast(str, response[0].id)
            for log_msg in response[1]:
                if log_msg.get("stream"):
                    LOGGER.info(log_msg["stream"].strip("\n"))
        else:
            docker_image = cast(str, response.id)
        LOGGER.info('docker image "%s" created', docker_image)
    if runtime:
        if runtime not in SUPPORTED_RUNTIMES:
            raise ValueError(
                f'invalid runtime "{runtime}" must be one of {SUPPORTED_RUNTIMES}'
            )
        docker_image = f"lambci/lambda:build-{runtime}"
        LOGGER.debug(
            'selected docker image "%s" based on provided runtime', docker_image
        )

    if sys.platform.lower() == "win32":
        LOGGER.debug("formatted docker mount path for Windows")
        work_dir = work_dir.replace("\\", "/")

    work_dir_mount = docker.types.Mount(
        target="/var/task", source=work_dir, type="bind"
    )
    pip_cmd = "python -m pip install -t /var/task -r /var/task/requirements.txt"

    LOGGER.info('using docker image "%s" to build deployment package...', docker_image)

    docker_run_args: Dict[str, Any] = {}
    if python_dontwritebytecode:
        docker_run_args["environment"] = "1"

    container = cast(
        Container,
        client.containers.run(
            image=docker_image,
            command=["/bin/sh", "-c", pip_cmd],
            auto_remove=True,
            detach=True,
            mounts=[work_dir_mount],
            **docker_run_args,
        ),
    )

    # 'stream' creates a blocking generator that allows for real-time logs.
    # this loop ends when the container 'auto_remove's itself.
    for log in cast(
        Iterator[bytes], container.logs(stdout=True, stderr=True, stream=True, tail=0)
    ):
        # without strip there are a bunch blank lines in the output
        LOGGER.info(log.decode().strip())


def _pip_has_no_color_option(python_path: str) -> bool:
    """Return boolean on whether pip is new enough to have --no-color option.

    pip v10 introduced this option, and it's used to minimize the effect of
    pip falsely indicating errors like the following:

    "ERROR: awscli 1.18.64 has requirement rsa<=3.5.0,>=3.1.2, but you'll
    have rsa 4.0 which is incompatible."

    An error like that (colored in red) will appear when there's a conflict
    between the host & target environments, which is not helpful in the
    context of building a Lambda zip that will never interact with the
    running python system.

    Ideally this mitigation (and this function by association) can be removed
    by an enhancement or replacement of pip for building the packages.

    """
    try:
        pip_version_string = subprocess.check_output(
            [
                python_path,
                "-c",
                "from __future__ import print_function;"
                "import pip;"
                "print(pip.__version__)",
            ]
        )
        if isinstance(pip_version_string, bytes):  # type: ignore
            pip_version_string = pip_version_string.decode()
        if int(pip_version_string.split(".", maxsplit=1)[0]) > 10:
            return True
    except (AttributeError, ValueError, subprocess.CalledProcessError):
        LOGGER.debug("error checking pip version; assuming it to be pre-v10")
    return False


# TODO refactor logic to breakup logic into smaller chunks
def _zip_package(  # pylint: disable=too-many-locals,too-many-statements
    package_root: str,
    *,
    dockerize_pip: DockerizePipArgTypeDef = False,
    excludes: Optional[List[str]] = None,
    follow_symlinks: bool = False,
    includes: List[str],
    pipenv_timeout: int = 300,
    python_dontwritebytecode: bool = False,
    python_exclude_bin_dir: bool = False,
    python_exclude_setuptools_dirs: bool = False,
    python_path: Optional[str] = None,
    requirements_files: Dict[str, bool],
    use_pipenv: bool = False,
    **kwargs: Any,
) -> Tuple[bytes, str]:
    """Create zip file in memory with package dependencies.

    Args:
        package_root: Base directory to copy files from.
        dockerize_pip: Whether to use docker or under what conditions docker will
            be used to run ``pip``.
        excludes: Exclusion patterns. Files matching those patterns will be
            excluded from the result. Exclusions take precedence over inclusions.
        follow_symlinks: If true, symlinks will be included in the resulting zip file.
        includes: Inclusion patterns. Only files  matching those patterns will be
            included in the result.
        pipenv_timeout: pipenv timeout in seconds.
        python_dontwritebytecode: Done write byte code.
        python_exclude_bin_dir: Exclude bin directory.
        python_exclude_setuptools_dirs: Exclude setuptools directories.
        python_path: Explicit python interpreter to be used. pipenv must be
            installed and executable using ``-m`` if provided.
        requirements_files: Map of requirement file names and whether they exist.
        use_pipenv: Whether to use pipenv to export a Pipfile as requirements.txt.

    Returns:
        Content of the ZIP file as a byte string and calculated hash of all the files

    """
    kwargs.setdefault("pipenv_timeout", 300)

    temp_root = DOT_RUNWAY_DIR
    if not temp_root.is_dir():
        temp_root.mkdir(parents=True)

    # exclude potential virtual environments in the package
    excludes = excludes or []
    excludes.append(".venv/")

    # pylint: disable=consider-using-with
    tmpdir = tempfile.TemporaryDirectory(prefix="cfngin", dir=temp_root)
    tmp_req = os.path.join(tmpdir.name, "requirements.txt")
    copydir(package_root, tmpdir.name, includes, excludes, follow_symlinks)
    tmp_req = handle_requirements(
        package_root=package_root,
        dest_path=tmpdir.name,
        requirements=requirements_files,
        python_path=python_path,
        use_pipenv=use_pipenv,
        pipenv_timeout=pipenv_timeout,
    )

    if should_use_docker(dockerize_pip):
        dockerized_pip(tmpdir.name, **kwargs)
    else:
        tmp_script = Path(tmpdir.name) / "__runway_run_pip_install.py"
        pip_cmd = [
            python_path or sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            tmpdir.name,
            "--requirement",
            tmp_req,
            "--no-color",
        ]

        subprocess_args: Dict[str, Any] = {}
        if python_dontwritebytecode:
            subprocess_args["env"] = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

        # Pyinstaller build or explicit python path
        if getattr(sys, "frozen", False) and not python_path:
            script_contents = os.linesep.join(
                [
                    "import runpy",
                    "from runway.utils imports argv",
                    f"with argv(*{json.dumps(pip_cmd[2:])}):",
                    '   runpy.run_module("pip", run_name="__main__")\n',
                ]
            )
            tmp_script.write_text(script_contents)
            cmd = [sys.executable, "run-python", str(tmp_script)]
        else:
            if not _pip_has_no_color_option(pip_cmd[0]):
                pip_cmd.remove("--no-color")
            cmd = pip_cmd

        LOGGER.info(
            "The following output from pip may include incompatibility errors. "
            "These can generally be ignored (pip will erroneously warn "
            "about conflicts between the packages in your Lambda zip and "
            "your host system)."
        )

        try:
            subprocess.check_call(cmd, **subprocess_args)
        except subprocess.CalledProcessError:
            raise PipError from None
        finally:
            if tmp_script.is_file():
                tmp_script.unlink()

    if python_exclude_bin_dir and os.path.isdir(os.path.join(tmpdir.name, "bin")):
        LOGGER.debug("Removing python /bin directory from Lambda files")
        shutil.rmtree(os.path.join(tmpdir.name, "bin"))
    if python_exclude_setuptools_dirs:
        for i in os.listdir(tmpdir.name):
            if i.endswith(".egg-info") or i.endswith(".dist-info"):
                LOGGER.debug("Removing directory %s from Lambda files", i)
                shutil.rmtree(os.path.join(tmpdir.name, i))

    req_files = _find_files(tmpdir.name, includes="**", follow_symlinks=False)
    contents, content_hash = _zip_files(req_files, tmpdir.name)
    if sys.version_info.major < 3:
        remove_error = OSError
    else:
        remove_error = PermissionError  # noqa pylint: disable=E
    try:
        tmpdir.cleanup()
    except remove_error:
        LOGGER.warning(
            'Error removing temporary Lambda build directory "%s", '
            "likely due to root-owned files it in. Delete it manually to "
            "reclaim space",
            tmpdir.name,
        )
    return contents, content_hash


def _head_object(
    s3_conn: S3Client, bucket: str, key: str
) -> Optional[HeadObjectOutputTypeDef]:
    """Retrieve information about an object in S3 if it exists.

    Args:
        s3_conn: S3 connection to use for operations.
        bucket: name of the bucket containing the key.
        key: name of the key to lookup.

    Returns:
        S3 object information, or None if the object does not exist.
        See the AWS documentation for explanation of the contents.

    Raises:
        botocore.exceptions.ClientError: any error from boto3 other than key
            not found is passed through.

    """
    try:
        return s3_conn.head_object(Bucket=bucket, Key=key)
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "404":
            return None
        raise


def _upload_code(
    s3_conn: S3Client,
    bucket: str,
    prefix: str,
    name: str,
    contents: Union[bytes, str],
    content_hash: str,
    payload_acl: PayloadAclTypeDef,
) -> Code:
    """Upload a ZIP file to S3 for use by Lambda.

    The key used for the upload will be unique based on the checksum of the
    contents. No changes will be made if the contents in S3 already match the
    expected contents.

    Args:
        s3_conn: S3 connection to use for operations.
        bucket: name of the bucket to create.
        prefix: S3 prefix to prepend to the constructed key name for
            the uploaded file
        name: desired name of the Lambda function. Will be used to construct a
            key name for the uploaded file.
        contents: byte string with the content of the file upload.
        content_hash: md5 hash of the contents to be uploaded.
        payload_acl: The canned S3 object ACL to be applied to the uploaded payload.

    Returns:
        CloudFormation Lambda Code object, pointing to the uploaded payload in S3.

    Raises:
        botocore.exceptions.ClientError: any error from boto3 is passed
            through.

    """
    LOGGER.debug("ZIP hash: %s", content_hash)
    key = f"{prefix}lambda-{name}-{content_hash}.zip"

    if _head_object(s3_conn, bucket, key):
        LOGGER.info("object already exists; not uploading: %s", key)
    else:
        LOGGER.info("uploading object: %s", key)
        s3_conn.put_object(
            Bucket=bucket,
            Key=key,
            Body=contents.encode() if isinstance(contents, str) else contents,
            ContentType="application/zip",
            ACL=payload_acl,
        )

    return Code(S3Bucket=bucket, S3Key=key)


def _check_pattern_list(
    patterns: Optional[Union[List[str], str]],
    key: str,
    default: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Validate file search patterns from user configuration.

    Acceptable input is a string (which will be converted to a singleton list),
    a list of strings, or anything falsy (such as None or an empty dictionary).
    Empty or unset input will be converted to a default.

    Args:
        patterns: Input from user configuration (YAML).
        key (str): Name of the configuration key the input came from,
            used for error display purposes.
        default: Value to return in case the input is empty or unset.

    Returns:
        Validated list of patterns.

    Raises:
        ValueError: If the input is unacceptable.

    """
    if not patterns:
        return default

    if isinstance(patterns, str):
        return [patterns]

    if isinstance(patterns, list) and all(isinstance(p, str) for p in patterns):  # type: ignore
        return patterns

    raise ValueError(
        f"Invalid file patterns in key '{key}': must be a string or " "list of strings"
    )


class _UploadFunctionOptionsTypeDef(TypedDict):
    """Type definition for the "options" argument of _upload_function.

    Attributes:
        include: File patterns to include in the payload.
        exclude: File patterns to exclude from the payload.
        path: Base path to retrieve files from. If not absolute, it
            will be interpreted as relative to the CFNgin configuration file
            directory, then converted to an absolutepath.

    """

    exclude: Optional[List[str]]
    include: Optional[List[str]]
    path: str


def _upload_function(
    s3_conn: S3Client,
    bucket: str,
    prefix: str,
    name: str,
    options: _UploadFunctionOptionsTypeDef,
    follow_symlinks: bool,
    payload_acl: PayloadAclTypeDef,
    sys_path: str,
) -> Code:
    """Build a Lambda payload from user configuration and uploads it to S3.

    Args:
        s3_conn: S3 connection to use for operations.
        bucket: name of the bucket to upload to.
        prefix: S3 prefix to prepend to the constructed key name for
            the uploaded file
        name: Desired name of the Lambda function. Will be used to
            construct a key name for the uploaded file.
        options: Configuration for how to build the payload.
        follow_symlinks: If true, symlinks will be included in the
            resulting zip file
        payload_acl: The canned S3 object ACL to be applied to the
            uploaded payload
        sys_path: Path that all actions are relative to.

    Returns:
        CloudFormation AWS Lambda Code object, pointing to the uploaded object in S3.

    Raises:
        ValueError: If any configuration is invalid.
        botocore.exceptions.ClientError: Any error from boto3 is passed
            through.

    """
    try:
        root = os.path.expanduser(options["path"])
    except KeyError as exc:
        raise ValueError(
            f"missing required property '{exc.args[0]}' in function '{name}'"
        ) from exc

    includes = _check_pattern_list(options.get("include"), "include", default=["**"])
    excludes = _check_pattern_list(options.get("exclude"), "exclude", default=[])

    LOGGER.debug("processing function: %s", name)

    # os.path.join will ignore other parameters if the right-most one is an
    # absolute path, which is exactly what we want.
    if not os.path.isabs(root):
        root = os.path.abspath(os.path.join(sys_path, root))
    requirements_files = find_requirements(root)
    if requirements_files:
        zip_contents, content_hash = _zip_package(
            root,
            includes=cast(List[str], includes),
            excludes=excludes,
            follow_symlinks=follow_symlinks,
            requirements_files=requirements_files,
            **options,
        )
    else:
        zip_contents, content_hash = _zip_from_file_patterns(
            root, cast(List[str], includes), cast(List[str], excludes), follow_symlinks
        )

    return _upload_code(
        s3_conn, bucket, prefix, name, zip_contents, content_hash, payload_acl
    )


def select_bucket_region(
    custom_bucket: Optional[str],
    hook_region: Optional[str],
    cfngin_bucket_region: Optional[str],
    provider_region: str,
) -> str:
    """Return the appropriate region to use when uploading functions.

    Select the appropriate region for the bucket where lambdas are uploaded in.

    Args:
        custom_bucket: The custom bucket name provided by the `bucket` kwarg of
            the aws_lambda hook, if provided.
        hook_region: The contents of the `bucket_region` argument to the hook.
        cfngin_bucket_region: The contents of the ``cfngin_bucket_region`` global
            setting.
        provider_region: The region being used by the provider.

    Returns:
        The appropriate region string.

    """
    region = None
    region = hook_region if custom_bucket else cfngin_bucket_region
    return region or provider_region


def upload_lambda_functions(context: CfnginContext, provider: Provider, **kwargs: Any):
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
        provider: Provider instance. (passed in by CFNgin)
        context: Context instance. (passed in by CFNgin)

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
                according to the include and exclude patterns. If no
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

            pre_deploy:
              - path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
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
    custom_bucket = cast(str, kwargs.get("bucket", ""))
    if not custom_bucket:
        if not context.bucket_name:
            raise ValueError("hook requires bucket argument or top-level cfngin_hook")
        bucket_name = context.bucket_name
        LOGGER.info("using default bucket from CFNgin: %s", bucket_name)
    else:
        bucket_name = custom_bucket
        LOGGER.info("using custom bucket: %s", bucket_name)

    custom_bucket_region = cast(str, kwargs.get("bucket_region", ""))
    if not custom_bucket and custom_bucket_region:
        raise ValueError("Cannot specify `bucket_region` without specifying `bucket`.")

    bucket_region = select_bucket_region(
        custom_bucket,
        custom_bucket_region,
        context.config.cfngin_bucket_region,
        provider.region or "us-east-1",
    )

    # Check if we should walk / follow symlinks
    follow_symlinks = kwargs.get("follow_symlinks", False)
    if not isinstance(follow_symlinks, bool):
        raise ValueError("follow_symlinks option must be a boolean")

    # Check for S3 object acl. Valid values from:
    # https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
    payload_acl = cast(PayloadAclTypeDef, kwargs.get("payload_acl", "private"))

    # Always use the global client for s3
    session = context.get_session(region=bucket_region)
    s3_client = session.client("s3")

    ensure_s3_bucket(s3_client, bucket_name, bucket_region)

    prefix = kwargs.get("prefix", "")

    results: Dict[str, Any] = {}
    for name, options in kwargs["functions"].items():
        sys_path = (
            os.path.dirname(context.config_path)
            if os.path.isfile(context.config_path)
            else context.config_path
        )
        results[name] = _upload_function(
            s3_client,
            bucket_name,
            prefix,
            name,
            options,
            follow_symlinks,
            payload_acl,
            str(sys_path),
        )

    return results
