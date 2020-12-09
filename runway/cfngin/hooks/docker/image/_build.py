"""Docker image build action.

Replicates the functionality of ``docker image build`` CLI command.

CLI docs: https://docs.docker.com/engine/reference/commandline/image_build/

"""
import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .._data_models import BaseModel, ElasticContainerRegistryRepository
from .._hook_data import DockerHookData

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # type: ignore pylint: disable=E

if TYPE_CHECKING:
    from docker.models.images import Image

    from ....context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


class DockerImageBuildApiOptions(BaseModel):
    """Options for controlling Docker."""

    _ctx = Optional["Context"]
    buildargs: Dict[str, Any]
    custom_context: bool = False
    extra_hosts: Optional[Dict[str, str]]
    forcerm: bool = False
    isolation: Optional[str]
    network_mode: str
    nocache: bool = False
    platform: Optional[str]
    pull: bool = False
    rm: bool = True
    squash: bool = False
    tag: str
    target: Optional[str]
    timeout: int
    use_config_proxy: bool = False

    def __init__(  # pylint: disable=too-many-arguments
        self,
        buildargs=None,  # type: Optional[Dict[str, Any]]
        custom_context=False,  # type: bool
        extra_hosts=None,  # type: Optional[Dict[str, Any]]
        forcerm=False,  # type: bool
        isolation=None,  # type: Optional[str]
        network_mode=None,  # type: Optional[str]
        nocache=False,  # type: bool
        platform=None,  # type: Optional[str]
        pull=False,  # type: bool
        rm=True,  # type: bool
        squash=False,  # type: bool
        tag=None,  # type: Optional[str]
        target=None,  # type: Optional[str]
        timeout=None,  # type: Optional[int]
        use_config_proxy=False,  # type: bool
        **kwargs,  # type: Any
    ):
        # type: (...) -> None
        """Instantiate class.

        Args:
            buildargs: Dict of build-time variables.
            custom_context: Optional if providing a path to a zip file.
            extra_hosts: Extra hosts to add to `/etc/hosts` in the building containers.
                Defined as a mapping of hostmane to IP address.
            forcerm: Always remove intermediate containers, even after unsuccessful
                builds.
            isolation: Isolation technology used during build.
            nocache: Don't use the cache when set to `True`.
            network_mode: Network mode for the run commands during build.
            platform: Set platform if server is multi-platform capable.
                Uses format `os[/arch[/variant]]`.
            pull: Download any updates to the FROM image in the Dockerfile.
            rm: Remove intermediate containers.
            squash: Squash the resulting image layers into a single layer.
            tag: Optional name and tag to apply to the base image when it is built.
            target: Name of the build-stage to build in a multi-stage Dockerfile.
            timeout: HTTP timeout.
            use_config_proxy: If `True` and if the docker client configuration file
                (~/.docker/config.json by default) contains a proxy configuration,
                the corresponding environment variables will be set in the container
                being built.

        """
        self._ctx = kwargs.get("context")  # type: Optional["Context"]
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
    """Args passed to image.build."""

    _ctx = Optional["Context"]
    docker: DockerImageBuildApiOptions
    dockerfile: str = "./Dockerfile"  # relative to path if path is a dir/zip
    path: Path
    repo: Optional[str]
    tags: List[str]

    def __init__(
        self,
        context=None,  # type: Optional["Context"]
        docker=None,  # type: Optional[Dict[str, Any]]
        dockerfile="./Dockerfile",  # type: str
        ecr_repo=None,  # type: Optional[Dict[str, Any]]
        path=None,  # type: Optional[Union[Path, str]]
        repo=None,  # type: Optional[str]
        tags=None,  # type: Optional[List[str]]
    ):
        # type: (...) -> None
        """Instantiate class.

        Args:
            context: CFNgin context object.
            docker: Options for `docker image build`.
            dockerfile: Path within the build cont4ext to the Dockerfile.
            ecr_repo: AWS Elastic Container Registry repository information.
                Providing this will automatically create the repo URI.
                If provided, do not provide ``repo``.
            path: Path to the directory continaing the Dockerfile.
            repo: URI of a non Docker Hub repository where the image will be stored.
                If providing one of the other repo values, leave this value empty.
            tags: List of tags to apply to the image.

        """
        docker = docker or {}
        self._ctx = context
        self.path = self._validate_path(path or Path.cwd())
        self.dockerfile = self._validate_dockerfile(self.path, dockerfile)
        self.repo = self.determine_repo(
            context=context,
            ecr_repo=self._validate_dict(ecr_repo, optional=True),
            repo=self._validate_str(repo, optional=True),
        )
        self.tags = self._validate_list_str(tags or ["latest"], required=True)

        if self.repo:
            docker.setdefault("tag", self.repo)
        self.docker = DockerImageBuildApiOptions.parse_obj(docker, context=self._ctx)

    @classmethod
    def _validate_dockerfile(cls, path, dockerfile):
        # type: (Path, str) -> None
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
                "Dockerfile does not exist at path provided: {}".format(fq_dockerfile)
            )
        return dockerfile

    @staticmethod
    def determine_repo(
        context=None,  # type: Optional["Context"]
        ecr_repo=None,  # type: Optional[Dict[str, Optional[str]]]
        repo=None,  # type: Optional[str]
    ):  # type: (...) -> Optional[str]
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


def build(**kwargs):  # type: (...) -> DockerHookData
    """Docker image build hook.

    Replicates the functionality of ``docker image build`` CLI command.

    """
    context = kwargs.pop("context")  # type: "Context"
    kwargs.pop("provider", None)  # not needed
    args = ImageBuildArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    image = docker_hook_data.client.images.build(  # type: "Image"
        path=str(args.path), **args.docker.dict()
    )
    for tag in args.tags:
        image.tag(args.repo, tag=tag)
    image.reload()
    LOGGER.info("created image %s with tags %s", image.short_id, ", ".join(image.tags))
    docker_hook_data.image = image
    return docker_hook_data.update_context(context)
