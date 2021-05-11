"""Docker image push hook.

Replicates the functionality of the ``docker image push`` CLI command.

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from ..data_models import BaseModel, DockerImage, ElasticContainerRegistryRepository
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImagePushArgs(BaseModel):
    """Args passed to image.push.

    Attributes:
        repo: URI of a non Docker Hub repository where the image will be stored.
        tags: List of tags to push.

    """

    repo: Optional[str]
    tags: List[str]

    def __init__(
        self,
        *,
        ecr_repo: Optional[Dict[str, Any]] = None,
        image: Optional[DockerImage] = None,
        repo: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Instantiate class.

        Args:
            ecr_repo: AWS Elastic Container Registry repository information.
                Providing this will automatically create the repo URI.
                If provided, do not provide ``repo``.
            image: Image to push.
            repo: URI of a non Docker Hub repository where the image will be stored.
                If providing one of the other repo values, leave this value empty.
            tags: List of tags to push.

        """
        super().__init__(**kwargs)
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
        return None


def push(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image push hook.

    Replicates the functionality of ``docker image push`` CLI command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImagePushArgs`.

    """
    kwargs.pop("provider", None)  # not needed
    args = ImagePushArgs.parse_obj(kwargs, context=context)
    docker_hook_data = DockerHookData.from_cfngin_context(context)
    LOGGER.info("pushing image %s...", args.repo)
    for tag in args.tags:
        docker_hook_data.client.images.push(repository=args.repo, tag=tag)
        LOGGER.info("successfully pushed image %s:%s", args.repo, tag)
    return docker_hook_data.update_context(context)
