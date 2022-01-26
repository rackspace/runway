"""Docker image build hook.

Replicates the functionality of the ``docker image build`` CLI command.

"""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from docker.models.images import Image
from pydantic import DirectoryPath, Field, validator

from .....utils import BaseModel
from ..data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class DockerImageBuildApiOptions(BaseModel):
    """Options for controlling Docker."""

    buildargs: Dict[str, Any] = {}
    """Dict of build-time variables that will be passed to Docker."""

    custom_context: bool = False
    """Whether to use custom context when providing a file object."""

    extra_hosts: Dict[str, str] = {}
    """Extra hosts to add to `/etc/hosts` in the build containers.
    Defined as a mapping of hostmane to IP address.

    """

    forcerm: bool = False
    """Always remove intermediate containers, even after unsuccessful builds."""

    isolation: Optional[str] = None
    """Isolation technology used during build."""

    network_mode: Optional[str] = None
    """Network mode for the run commands during build."""

    nocache: bool = False
    """Whether to use cache."""

    platform: Optional[str] = None
    """Set platform if server is multi-platform capable.
    Uses format ``os[/arch[/variant]]``.

    """

    pull: bool = False
    """Whether to download any updates to the FROM image in the Dockerfile."""

    rm: bool = True
    """Whether to remove intermediate containers."""

    squash: bool = False
    """Whether to squash the resulting image layers into a single layer."""

    tag: Optional[str] = None
    """Optional name and tag to apply to the base image when it is built."""

    target: Optional[str] = None
    """Name of the build-stage to build in a multi-stage Dockerfile."""

    timeout: Optional[int] = None
    """HTTP timeout."""

    use_config_proxy: bool = False
    """If ``True`` and if the Docker client configuration file
    (``~/.docker/config.json`` by default) contains a proxy configuration,
    the corresponding environment variables will be set in the container
    being built.

    """


class ImageBuildArgs(BaseModel):
    """Args passed to image.build."""

    _ctx: Optional[CfnginContext] = Field(default=None, alias="context", export=False)

    ecr_repo: Optional[ElasticContainerRegistryRepository] = None  # depends on _ctx
    """AWS Elastic Container Registry repository information.
    Providing this will automatically construct the repo URI.
    If provided, do not provide ``repo``.

    If using a private registry, only ``repo_name`` is required.
    If using a public registry, ``repo_name`` and ``registry_alias``.

    """

    path: DirectoryPath = Path.cwd()
    """Path to the directory containing the Dockerfile."""

    dockerfile: str = "Dockerfile"  # depends on path for validation
    """Path within the build context to the Dockerfile."""

    repo: Optional[str] = None  # depends on ecr_repo
    """URI of a non Docker Hub repository where the image will be stored."""

    docker: DockerImageBuildApiOptions = DockerImageBuildApiOptions()  # depends on repo
    """Options for ``docker image build``."""

    tags: List[str] = ["latest"]
    """List of tags to apply to the image."""

    @validator("docker", pre=True, always=True, allow_reuse=True)
    def _set_docker(
        cls,
        v: Union[Dict[str, Any], DockerImageBuildApiOptions, Any],
        values: Dict[str, Any],
    ) -> Any:
        """Set the value of ``docker``."""
        repo = values["repo"]
        if repo:
            if isinstance(v, dict):
                v.setdefault("tag", repo)
            elif isinstance(v, DockerImageBuildApiOptions) and not v.tag:
                v.tag = repo
        return v

    @validator("ecr_repo", pre=True, allow_reuse=True)
    def _set_ecr_repo(cls, v: Any, values: Dict[str, Any]) -> Any:
        """Set the value of ``ecr_repo``."""
        if v and isinstance(v, dict):
            return ElasticContainerRegistryRepository.parse_obj(
                {
                    "repo_name": v.get("repo_name"),
                    "registry": ElasticContainerRegistry.parse_obj(
                        {
                            "account_id": v.get("account_id"),
                            "alias": v.get("registry_alias"),
                            "aws_region": v.get("aws_region"),
                            "context": values.get("context"),
                        }
                    ),
                }
            )
        return v

    @validator("repo", pre=True, always=True, allow_reuse=True)
    def _set_repo(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Set the value of ``repo``."""
        if v:
            return v

        ecr_repo: Optional[ElasticContainerRegistryRepository] = values.get("ecr_repo")
        if ecr_repo:
            return ecr_repo.fqn

        return None

    @validator("dockerfile", pre=True, always=True, allow_reuse=True)
    def _validate_dockerfile(cls, v: Any, values: Dict[str, Any]) -> Any:
        """Validate ``dockerfile``."""
        path: Path = values["path"]
        dockerfile = path / v
        if not dockerfile.is_file():
            raise ValueError(
                f"Dockerfile does not exist at path provided: {dockerfile}"
            )
        return v


def build(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image build hook.

    Replicates the functionality of ``docker image build`` CLI command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImageBuildArgs`.

    """
    args = ImageBuildArgs.parse_obj({"context": context, **kwargs})
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    image, logs = cast(
        Tuple[Image, Iterator[Dict[str, str]]],
        docker_hook_data.client.images.build(path=str(args.path), **args.docker.dict()),
    )
    for msg in logs:  # iterate through JSON log messages
        if "stream" in msg:  # log if they contain a message
            LOGGER.info(msg["stream"].strip())  # remove any new line characters
    for tag in args.tags:
        image.tag(args.repo, tag=tag)
    image.reload()
    LOGGER.info("created image %s with tags %s", image.short_id, ", ".join(image.tags))
    docker_hook_data.image = DockerImage(image=image)
    return docker_hook_data.update_context(context)
