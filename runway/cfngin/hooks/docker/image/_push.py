"""Docker image push hook.

Replicates the functionality of the ``docker image push`` CLI command.

.. rubric:: Hook Path

``runway.cfngin.hooks.docker.image.push``

.. rubric:: Args

ecr_repo (Optional[Dict[str, Optional[str]]])
    Information describing an ECR repository. This is used to construct the repository URL.
    If providing a value for this field, do not provide a value for ``image`` or ``repo``.

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

image (Optional[DockerImage])
    A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object.
    This can be retrieved from ``hook_data`` for a preceding *build* using the
    :ref:`hook_data Lookup <hook_data lookup>`.

    If providing a value for this field, do not provide a value for ``ecr_repo`` or ``repo``.
repo (Optional[str])
    URI of a non Docker Hub repository where the image will be stored.
    If providing one of the other repo values or ``image``, leave this value empty.
tags (Optional[List[str]])
    List of tags push. (*default:* ``["latest"]``)

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

    stacks:
      ecr-lambda-function:
        class_path: blueprints.EcrFunction
        variables:
          ImageUri: ${hook_data docker.image.uri.latest}

"""
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from ....context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImagePushArgs(BaseModel):
    """Args passed to image.push."""

    def __init__(
        self,
        ecr_repo=None,  # type: Optional[Dict[str, Any]]
        image=None,  # type: Optional[DockerImage]
        repo=None,  # type: Optional[str]
        tags=None,  # type: Optional[List[str]]
        **kwargs  # type: Any
    ):  # type: (...) -> None
        """Instantiate class."""
        self.repo = self.determine_repo(
            context=kwargs.get("context"), ecr_repo=ecr_repo, image=image, repo=repo
        )
        if image and not tags:
            tags = image.tags
        self.tags = self._validate_list_str(tags or ["latest"], required=True)

    @staticmethod
    def determine_repo(
        context=None,  # type: Optional["Context"]
        ecr_repo=None,  # type: Optional[Dict[str, Optional[str]]]
        image=None,  # type: Optional[DockerImage]
        repo=None,  # type: Optional[str]
    ):  # type: (...) -> Optional[str]
        """Determine repo URI.

        Args:
            context: CFNgin context.
            ecr_repo: AWS Elastic Container Registry options.
            image: Docker image object.
            repo: URI of a non Docker Hub repository.

        """
        if repo:
            return repo
        if isinstance(image, DockerImage):
            return image.repo
        if ecr_repo:
            return ElasticContainerRegistryRepository.parse_obj(
                ecr_repo, context=context
            ).fqn
        return None


def push(**kwargs):  # type: (...) -> DockerHookData
    """Docker image push hook.

    Replicates the functionality of ``docker image push`` CLI command.

    """
    context = kwargs.pop("context")  # type: "Context"
    kwargs.pop("provider", None)  # not needed
    args = ImagePushArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    LOGGER.info("pushing image %s...", args.repo)
    for tag in args.tags:
        docker_hook_data.client.images.push(repository=args.repo, tag=tag)
        LOGGER.info("successfully pushed image %s:%s", args.repo, tag)
    return docker_hook_data.update_context(context)
