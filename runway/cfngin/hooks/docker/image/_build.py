"""Docker image build hook.

Replicates the functionality of the ``docker image build`` CLI command.

"""
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

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class DockerImageBuildApiOptions(BaseModel):
    """Options for controlling Docker.

    Attributes:
        buildargs: Dict of build-time variables that will be passed to Docker.
        custom_context: Whether to use custom context when providing a file object.
        extra_hosts: Extra hosts to add to `/etc/hosts` in the build containers.
            Defined as a mapping of hostmane to IP address.
        forcerm: Always remove intermediate containers, even after unsuccessful builds.
        isolation: Isolation technology used during build.
        network_mode: Network mode for the run commands during build.
        nocache: Whether to use cache.
        platform: Set platform if server is multi-platform capable.
            Uses format ``os[/arch[/variant]]``.
        pull: Whether to download any updates to the FROM image in the Dockerfile.
        rm: Whether to remove intermediate containers.
        squash: Whether to squash the resulting image layers into a single layer.
        tag: Optional name and tag to apply to the base image when it is built.
        target: Name of the build-stage to build in a multi-stage Dockerfile.
        timeout: HTTP timeout.
        use_config_proxy: If ``True`` and if the Docker client configuration file
            (``~/.docker/config.json`` by default) contains a proxy configuration,
            the corresponding environment variables will be set in the container
            being built.

    """

    buildargs: Dict[str, Any]
    custom_context: bool
    extra_hosts: Optional[Dict[str, str]]
    forcerm: bool
    isolation: Optional[str]
    network_mode: Optional[str]
    nocache: bool
    platform: Optional[str]
    pull: bool
    rm: bool
    squash: bool
    tag: Optional[str]
    target: Optional[str]
    timout: Optional[int]
    use_config_proxy: bool

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        buildargs: Optional[Dict[str, Any]] = None,
        custom_context: bool = False,
        extra_hosts: Optional[Dict[str, Any]] = None,
        forcerm: bool = False,
        isolation: Optional[str] = None,
        network_mode: Optional[str] = None,
        nocache: bool = False,
        platform: Optional[str] = None,
        pull: bool = False,
        rm: bool = True,  # pylint: disable=invalid-name
        squash: bool = False,
        tag: Optional[str] = None,
        target: Optional[str] = None,
        timeout: Optional[int] = None,
        use_config_proxy: bool = False,
        **kwargs: Any,
    ) -> None:
        """Instantiate class.

        Args:
            buildargs: Dict of build-time variables that will be passed to Docker.
            custom_context: Whether to use custom context when providing a file object.
            extra_hosts: Extra hosts to add to `/etc/hosts` in the build containers.
                Defined as a mapping of hostmane to IP address.
            forcerm: Always remove intermediate containers, even after unsuccessful builds.
            isolation: Isolation technology used during build.
            network_mode: Network mode for the run commands during build.
            nocache: Whether to use cache.
            platform: Set platform if server is multi-platform capable.
                Uses format ``os[/arch[/variant]]``.
            pull: Whether to download any updates to the FROM image in the Dockerfile.
            rm: Whether to remove intermediate containers.
            squash: Whether to squash the resulting image layers into a single layer.
            tag: Optional name and tag to apply to the base image when it is built.
            target: Name of the build-stage to build in a multi-stage Dockerfile.
            timeout: HTTP timeout.
            use_config_proxy: If ``True`` and if the Docker client configuration file
                (``~/.docker/config.json`` by default) contains a proxy configuration,
                the corresponding environment variables will be set in the container
                being built.

        """
        super().__init__(**kwargs)
        self.buildargs = self._validate_dict(buildargs)
        self.custom_context = self._validate_bool(custom_context)
        self.extra_hosts = self._validate_dict(extra_hosts, optional=True)
        self.forcerm = self._validate_bool(forcerm)
        self.isolation = self._validate_str(isolation, optional=True)
        self.network_mode = self._validate_str(network_mode, optional=True)
        self.nocache = self._validate_bool(nocache)
        self.platform = self._validate_str(platform, optional=True)
        self.pull = self._validate_bool(pull)
        self.rm = self._validate_bool(rm)  # pylint: disable=invalid-name
        self.squash = self._validate_bool(squash)
        self.tag = self._validate_str(tag, optional=True)
        self.target = self._validate_str(target, optional=True)
        self.timeout = self._validate_int(timeout, optional=True)
        self.use_config_proxy = self._validate_bool(use_config_proxy)


class ImageBuildArgs(BaseModel):
    """Args passed to image.build.

    Attributes:
        docker: Options for ``docker image build``.
        dockerfile: Path within the build context to the Dockerfile.
        ecr_repo: AWS Elastic Container Registry repository information.
            Providing this will automatically construct the repo URI.
            If provided, do not provide ``repo``.

            If using a private registry, only ``repo_name`` is required.
            If using a public registry, ``repo_name`` and ``registry_alias``.
        path: Path to the directory containing the Dockerfile.
        repo: URI of a non Docker Hub repository where the image will be stored.
        tags: List of tags to apply to the image.

    """

    docker: DockerImageBuildApiOptions
    dockerfile: str
    path: Path
    repo: Optional[str]
    tags: List[str]

    def __init__(
        self,
        *,
        context: Optional[CfnginContext] = None,
        docker: Optional[Dict[str, Any]] = None,
        dockerfile: str = "./Dockerfile",
        ecr_repo: Optional[Dict[str, Optional[str]]] = None,
        path: Optional[Union[Path, str]] = None,
        repo: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: CFNgin context object.
            docker: Options for ``docker image build``.
            dockerfile: Path within the build context to the Dockerfile.
            ecr_repo: AWS Elastic Container Registry repository information.
                Providing this will automatically create the repo URI.
                If provided, do not provide ``repo``.
            path: Path to the directory containing the Dockerfile.
            repo: URI of a non Docker Hub repository where the image will be stored.
                If providing one of the other repo values, leave this value empty.
            tags: List of tags to apply to the image. If not provided, ``["latest"]``
                will be used.

        """
        super().__init__(context=context)
        docker = docker or {}
        self.path = self._validate_path(path or Path.cwd(), must_exist=True)
        self.dockerfile = self._validate_dockerfile(self.path, dockerfile)
        self.repo = self.determine_repo(
            context=context,
            ecr_repo=self._validate_dict(ecr_repo, optional=True),
            repo=self._validate_str(repo, optional=True),
        )
        self.tags = cast(
            List[str], self._validate_list_str(tags or ["latest"], required=True)
        )

        if self.repo:
            docker.setdefault("tag", self.repo)
        self.docker = DockerImageBuildApiOptions.parse_obj(docker)

    @classmethod
    def _validate_dockerfile(cls, path: Path, dockerfile: str) -> str:
        """Validate Dockerfile."""
        if path.is_file():
            if path.name.endswith("Dockerfile"):
                raise ValueError(
                    cls.__name__ + ".path should not reference the Dockerfile directly"
                    " but the directory containing the Dockerfile"
                )
            return dockerfile
        fq_dockerfile = path / dockerfile
        if not fq_dockerfile.is_file():
            raise ValueError(
                f"Dockerfile does not exist at path provided: {fq_dockerfile}"
            )
        return dockerfile

    @staticmethod
    def determine_repo(
        context: Optional[CfnginContext] = None,
        ecr_repo: Optional[Dict[str, Optional[str]]] = None,
        repo: Optional[str] = None,
    ) -> Optional[str]:
        """Determine repo URI.

        Args:
            context: CFNgin context.
            ecr_repo: AWS Elastic Container Registry options.
            repo: URI of a non Docker Hub repository.

        """
        if repo:
            return repo
        if ecr_repo:
            return ElasticContainerRegistryRepository.parse_obj(
                ecr_repo, context=context
            ).fqn
        return None


def build(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image build hook.

    Replicates the functionality of ``docker image build`` CLI command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImageBuildArgs`.

    """
    kwargs.pop("provider", None)  # not needed
    args = ImageBuildArgs.parse_obj(kwargs, context=context)
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
    LOGGER.info(
        "created image %s with tags %s",
        cast(str, image.short_id),
        ", ".join(cast(List[str], image.tags)),
    )
    docker_hook_data.image = DockerImage(image=image)
    return docker_hook_data.update_context(context)
