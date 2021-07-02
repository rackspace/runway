"""Docker image remove hook.

Replicates the functionality of the ``docker image remove`` CLI command.

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from docker.errors import ImageNotFound

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImageRemoveArgs(BaseModel):
    """Args passed to image.remove.

    Attributes:
        force: Whether to force the removal of the image.
        noprune: Whether to delete untagged parents.
        repo: URI of a non Docker Hub repository where the image will be stored.
        tags: List of tags to remove.

    """

    force: bool
    noprune: bool
    repo: Optional[str]
    tags: List[str]

    def __init__(
        self,
        *,
        ecr_repo: Optional[Dict[str, Any]] = None,
        force: bool = False,
        image: DockerImage = None,
        noprune: bool = False,
        repo: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Instantiate class.

        Args:
            ecr_repo: AWS Elastic Container Registry repository information.
                Providing this will automatically create the repo URI.
                If provided, do not provide ``repo``.
            force: Whether to force the removal of the image.
            image: Image to push.
            noprune: Whether to delete untagged parents.
            repo: URI of a non Docker Hub repository where the image will be stored.
                If providing one of the other repo values, leave this value empty.
            tags: List of tags to remove.

        """
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

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImageRemoveArgs`.

    """
    kwargs.pop("provider", None)  # not needed
    args = ImageRemoveArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    LOGGER.info("removing local image %s...", args.repo)
    for tag in args.tags:
        image = f"{args.repo}:{tag}"
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
