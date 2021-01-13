"""Docker image build hook.

Replicates the functionality of the ``docker image build`` CLI command.

.. rubric:: Hook Path

``runway.cfngin.hooks.docker.image.build``

.. rubric:: Args

docker (Optional[Dict[str, Any]])
    Options for ``docker image build``.

    buildargs (Optional[Dict[str, str]])
        Dict of build-time variables.
    custom_context (bool)
        Optional if providing a path to a zip file. (*default:* ``False``)
    extra_hosts (Optional[Dict[str, str]])
        Extra hosts to add to `/etc/hosts` in the building containers.
        Defined as a mapping of hostmane to IP address.
    forcerm (bool)
        Always remove intermediate containers, even after unsuccessful builds.
        (*default:* ``False``)
    isolation (Optional[str])
        Isolation technology used during build.
    network_mode (Optional[str])
        Network mode for the run commands during build.
    nocache (bool)
        Don't use cache when set to ``True``. (*default:* ``False``)
    platform (Optional[str])
        Set platform if server is multi-platform capable.
        Uses format ``os[/arch[/variant]]``.
    pull (bool)
        Download any updates to the FROM image in the Dockerfile. (*default:* ``False``)
    rm (bool)
        Remove intermediate containers. (*default:* ``True``)
    squash (bool)
        Squash the resulting image layers into a single layer. (*default:* ``False``)
    tag (Optional[str])
        Optional name and tag to apply to the base image when it is built.
    target (Optional[str])
        Name of the build-stage to build in a multi-stage Dockerfile.
    timeout (Optional[int])
        HTTP timeout.
    use_config_proxy (bool)
        If ``True`` and if the docker client configuration file
        (``~/.docker/config.json`` by default) contains a proxy configuration,
        the corresponding environment variables will be set in the container
        being built. (*default:* ``False``)

dockerfile (Optional[str])
    Path within the build cont4ext to the Dockerfile. *(default: ./Dockerfile)*
ecr_repo (Optional[Dict[str, Optional[str]]])
    Information describing an ECR repository. This is used to construct the repository URL.
    If providing a value for this field, do not provide a value for ``repo``.

    If using a private registry, only ``repo_name`` is required.
    If using a public registry, ``repo_name`` and ``registry_alias``.

    account_id (Optional[str])
        AWS account ID that owns the registry being logged into. If not provided,
        it will be acquired automatically if needed.
    aws_region (Optional[str])
        AWS region where the registry is located. If not provided, it will be acquired
        automatically if needed.
    registry_alias (Optional[str])
        If it is a public repository, provide the alias.
    repo_name (str)
        The name of the repository

path (Optional[str])
    Path to the directory continaing the Dockerfile. *(defaults to the current working directory)*
repo (Optional[str])
    URI of a non Docker Hub repository where the image will be stored.
    If providing one of the other repo values, leave this value empty.
tags (Optional[List[str]])
    List of tags to apply to the image. (*default:* ``["latest"]``)

.. rubric:: Returns

The following are values accessible with the :ref:`hook_data Lookup <hook_data lookup>`
under the ``data_key`` of ``docker`` (do not specify a ``data_key`` for the hook, this
is handled automatically).

image (DockerImage)
    A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object for the
    image that was just built.

    .. important::
      Each execution of this hook overwrites any previous values stored in this attribute.
      It is advices to consume the resulting image object after it has been built, if it
      will be consumed by a later hook/stack.

.. rubric:: Example
.. code-block:: yaml

    pre_build:
      - path: runway.cfngin.hooks.docker.login
        args:
          ecr: true
          password: ${ecr login-password}
      - path: runway.cfngin.hooks.docker.image.build
        args:
          ecr_repo:
            repo_name: ${cfn ${namespace}-test-ecr.Repository}
          tags:
            - latest
            - python3.9
      - path: runway.cfngin.hooks.docker.image.push
        args:
          image: ${hook_data docker.image}

"""
import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union  # pylint: disable=W

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # type: ignore pylint: disable=E

if TYPE_CHECKING:
    from ....context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


class DockerImageBuildApiOptions(BaseModel):
    """Options for controlling Docker."""

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
        **kwargs  # type: Any  # pylint: disable=unused-argument
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
            network_mode: Network mode for the run commands during build.
            nocache: Don't use the cache when set to `True`.
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
        self.path = self._validate_path(path or Path.cwd(), must_exist=True)
        self.dockerfile = self._validate_dockerfile(self.path, dockerfile)
        self.repo = self.determine_repo(
            context=context,
            ecr_repo=self._validate_dict(ecr_repo, optional=True),
            repo=self._validate_str(repo, optional=True),
        )
        self.tags = self._validate_list_str(tags or ["latest"], required=True)

        if self.repo:
            docker.setdefault("tag", self.repo)
        self.docker = DockerImageBuildApiOptions.parse_obj(docker)

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
    image, logs = docker_hook_data.client.images.build(
        path=str(args.path), **args.docker.dict()
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
