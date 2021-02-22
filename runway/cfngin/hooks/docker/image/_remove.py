"""Docker image build hook.

Replicates the functionality of the ``docker image remove`` CLI command.

.. rubric:: Hook Path

``runway.cfngin.hooks.docker.image.remove``

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

force (bool)
    Force removal of the image. (*default:* ``False``)
image (Optional[DockerImage])
    A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object.
    If providing an ``Image`` object from ```hook_data``, it will be removed from
    from there as well.

    If providing a value for this field, do not provide a value for ``ecr_repo`` or ``repo``.
noprune (bool)
    Do not delete untagged parents. (*default:* ``False``)
repo (Optional[str])
    URI of a non Docker Hub repository where the image is stored.
    If providing one of the other repo values or ``image``, leave this value empty.
tags (Optional[List[str]])
    List of tags delete. (*default:* ``["latest"]``)

.. rubric:: Example
.. code-block:: yaml

    pre_deploy:
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
          tags:
            - latest
            - python3.9

    stacks:
      ...

    post_deploy:
      - path: runway.cfngin.hooks.docker.image.remove
        args:
          image: ${hook_data docker.image}
          tags:
            - latest
            - python3.9

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from docker.errors import ImageNotFound

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from .....context.cfngin import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImageRemoveArgs(BaseModel):
    """Args passed to image.remove."""

    def __init__(
        self,
        *,
        ecr_repo: Optional[Dict[str, Any]] = None,
        force: bool = False,
        image: DockerImage = None,
        noprune: bool = False,
        repo: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any
    ) -> None:
        """Instantiate class."""
        super().__init__(**kwargs)
        self.force = force
        self.noprune = noprune
        self.repo = self.determine_repo(
            context=self._ctx, ecr_repo=ecr_repo, image=image, repo=repo
        )
        if image and not tags:
            tags = image.tags
        self.tags = cast(
            List[str], self._validate_list_str(tags or ["latest"], required=True)
        )

    @staticmethod
    def determine_repo(
        context: Optional[CfnginContext] = None,
        ecr_repo: Optional[Dict[str, Optional[str]]] = None,
        image: Optional[DockerImage] = None,
        repo: Optional[str] = None,
    ) -> Optional[str]:
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
        raise ValueError("a repo must be specified")


def remove(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image push remove.

    Replicates the functionality of ``docker image push`` CLI command.

    """
    kwargs.pop("provider", None)  # not needed
    args = ImageRemoveArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    LOGGER.info("removing local image %s...", args.repo)
    for tag in args.tags:
        image = "{}:{}".format(args.repo, tag)
        try:
            docker_hook_data.client.images.remove(
                image=image, force=args.force, noprune=args.noprune
            )
            LOGGER.info("successfully removed local image %s", image)
        except ImageNotFound:
            LOGGER.warning("local image %s does not exist", image)
    if docker_hook_data.image and kwargs.get("image"):
        if kwargs["image"].id == docker_hook_data.image.id:
            docker_hook_data.image = None  # clear out the image that was set
    return docker_hook_data.update_context(context)
