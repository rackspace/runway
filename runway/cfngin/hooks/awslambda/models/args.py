"""Argument data models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from pydantic import DirectoryPath, Extra, Field, FilePath, validator

from .....config.models.utils import resolve_path_field
from .....utils import BaseModel
from ...base import HookArgsBaseModel

if TYPE_CHECKING:
    from typing import Callable


class DockerOptions(BaseModel):
    """Docker options."""

    disabled: bool = False
    """Explicitly disable the use of docker (default ``False``).

    If not disabled and Docker is unreachable, the hook will result in an error.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            disabled: true

    """

    extra_files: List[str] = []
    """List of absolute file paths within the Docker container to copy into the deployment package.

    Some Python packages require extra OS libraries (``*.so``) files at runtime.
    These files need to be included in the deployment package for the Lambda Function to run.
    List the files here and the hook will handle copying them into the deployment package.

    The file name may end in a wildcard (``*``) to accommodate ``.so`` files that
    end in an variable number (see example below).

    If the file does not exist, it will result in an error.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            extra_files:
              - /usr/lib64/mysql/libmysqlclient.so.*
              - /usr/lib64/libxmlsec1-openssl.so

    """

    file: Optional[FilePath] = None
    """Dockerfile to use to build an image for use in this process.

    This, ``image`` , or ``runtime`` must be provided.
    If not provided, ``image`` will be used.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            file: Dockerfile

    """

    image: Optional[str] = None
    """Docker image to use. If the image does not exist locally, it will be pulled.

    This, ``file`` (takes precedence), or ``runtime`` must be provided.
    If only ``runtime`` is provided, it will be used to determine the appropriate
    image to use.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            image: public.ecr.aws/sam/build-python3.9:latest

    """

    name: Optional[str] = None
    """When providing a Dockerfile, this will be the name applied to the resulting image.
    It is the equivalent to ``name`` in the ``name:tag`` syntax of the
    ``docker build [--tag, -t]`` command option.

    If not provided, a default image name is used.

    This field is ignore unless ``file`` is provided.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            file: Dockerfile
            name: ${namespace}.runway.awslambda

    """

    pull: bool = True
    """Always download updates to the specified image before use.
    When building an image, the ``FROM`` image will be updated during the build
    process  (default ``True``).

    .. rubric:: Example
    .. code-block:: yaml

        args:
          docker:
            pull: false

    """

    class Config:
        """Model configuration."""

        extra = Extra.ignore

    _resolve_path_fields = cast(
        "classmethod[Callable[..., Any]]",
        validator("file", allow_reuse=True)(resolve_path_field),
    )


class AwsLambdaHookArgs(HookArgsBaseModel):
    """Base class for AWS Lambda hook arguments."""

    bucket_name: str
    """Name of the S3 Bucket where deployment package is/will  be stored.
    The Bucket must be in the same region the Lambda Function is being deployed in.

    """

    cache_dir: Optional[Path] = None
    """Explicitly define the directory location.
    Must be an absolute path or it will be relative to the CFNgin module directory.

    """

    compatible_architectures: Optional[List[str]] = None
    """A list of compatible instruction set architectures.
    (https://docs.aws.amazon.com/lambda/latest/dg/foundation-arch.html)

    Only used by Lambda Layers.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          compatible_architectures:
            - x86_64
            - arm64

    """

    compatible_runtimes: Optional[List[str]] = None
    """A list of compatible function runtimes.
    When provided, the ``runtime`` being used to build the deployment package
    must be included in the list or an error will be raised.

    Only used by Lambda Layers.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          compatible_runtimes:
            - python3.8
            - python3.9

    """

    docker: DockerOptions = DockerOptions()
    """Docker options."""

    extend_gitignore: List[str] = []
    """gitignore rules that should be added to the rules already defined in a
    ``.gitignore`` file in the source code directory.
    This can be used with or without an existing file.
    Files that match a gitignore rule will not be included in the deployment package.

    ``.git/`` & ``.gitignore`` will always be added.

    .. important:: This only applies to files in the ``source_code`` directory.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          extend_gitignore:
            - cfngin.yml
            - poetry.lock
            - poetry.toml
            - pyproject.toml

    """

    license: Optional[str] = Field(default=None, max_length=256)
    """The layer's software license. Can be any of the following:

    - A SPDX license identifier (e.g. ``Apache-2.0``).
    - The URL of a license hosted on the internet (e.g.
      ``https://opensource.org/licenses/Apache-2.0``).
    - The full text of the license.

    Only used by Lambda Layers.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          license: Apache-2.0

    """

    object_prefix: Optional[str] = None
    """Prefix to add to the S3 Object key.

    The object will always be prefixed with ``awslambda/functions``.
    If provided, the value will be added to the end of the static prefix
    (e.g. ``awslambda/<functions|layers>/<object_prefix>/<file name>``).

    """

    runtime: Optional[str] = None
    """Runtime of the Lambda Function
    (https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

    This, ``docker.file``, or ``docker.image`` must be provided.
    If ``docker.disabled``, this field is required.

    When provided, the runtime available on the build system (Docker container
    or localhost) will be checked against this value. If they do not match,
    an error will be raised.

    If the defined or detected runtime ever changes so that it no longer
    matches the deployment package in S3, the deployment package in S3 will be
    deleted and a new one will be built and uploaded.

    """

    slim: bool = True
    """Automatically remove information and caches from dependencies (default ``True``).
    This is done by applying gitignore rules to the dependencies.
    These rules vary by language/runtime.

    """

    source_code: DirectoryPath
    """Path to the Lambda Function source code.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          source_code: ./my/package

    """

    use_cache: bool = True
    """Whether to use a cache directory with pip that will persist builds (default ``True``)."""

    _resolve_path_fields = cast(
        "classmethod[Callable[..., Any]]",
        validator("cache_dir", "source_code", allow_reuse=True)(resolve_path_field),
    )

    @validator("runtime", always=True, allow_reuse=True)
    def _validate_runtime_or_docker(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        """Validate that either runtime is provided or Docker image is provided."""
        if v:  # if runtime was provided, we don't need to check anything else
            return v
        docker: DockerOptions = values["docker"]
        if docker.disabled:
            raise ValueError("runtime must be provided if docker.disabled is True")
        if not (docker.file or docker.image):
            raise ValueError("docker.file, docker.image, or runtime is required")
        return v


class PythonHookArgs(AwsLambdaHookArgs):
    """Hook arguments for a Python AWS Lambda deployment package."""

    extend_pip_args: Optional[List[str]] = None
    """Additional arguments that should be passed to ``pip install``.

    .. important::
      When providing this field, be careful not to duplicate any of the arguments
      passed by this hook (e.g. ``--requirements``, ``--target``, ``--no-input``).
      Providing duplicate arguments will result in an error.

    .. rubric:: Example
    .. code-block:: yaml

        args:
          extend_pip_args:
            - '--proxy'
            - '[user:passwd@]proxy.server:port'

    """

    slim: bool = True
    """Automatically remove information and caches from dependencies (default ``True``).
    This is done by applying the following gitignore rules to the dependencies:

    - ``**/*.dist-info*``
    - ``**/*.py[c|d|i|o]``
    - ``**/*.so``
    - ``**/__pycache__*``

    """

    strip: bool = True
    """Whether or not to strip binary files from the dependencies (default ``True``).
    This only takes effect if ``slim: true``.

    If false, the gitignore rule ``**/*.so`` is not used.

    """

    use_pipenv: bool = True
    """Whether pipenv should be used if determined appropriate."""

    use_poetry: bool = True
    """Whether poetry should be used if determined appropriate."""

    class Config:
        """Model configuration."""

        extra = Extra.ignore
