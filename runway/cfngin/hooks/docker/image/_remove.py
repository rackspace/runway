"""Docker image remove hook.

Replicates the functionality of the ``docker image remove`` CLI command.

"""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from docker.errors import ImageNotFound
from pydantic import Field, validator

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


class ImageRemoveArgs(BaseModel):
    """Args passed to image.remove."""

    _ctx: Optional[CfnginContext] = Field(default=None, alias="context", export=False)

    ecr_repo: Optional[ElasticContainerRegistryRepository] = None  # depends on _ctx
    """AWS Elastic Container Registry repository information.
    Providing this will automatically construct the repo URI.
    If provided, do not provide ``repo``.

    If using a private registry, only ``repo_name`` is required.
    If using a public registry, ``repo_name`` and ``registry_alias``.

    """

    force: bool = False
    """Whether to force the removal of the image."""

    image: Optional[DockerImage] = None
    """Image to push."""

    noprune: bool = False
    """Whether to delete untagged parents."""

    repo: Optional[str] = None  # depends on ecr_repo & image
    """URI of a non Docker Hub repository where the image will be stored."""

    tags: List[str] = []  # depends on image
    """List of tags to remove."""

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

        image: Optional[DockerImage] = values.get("image")
        if image:
            return image.repo

        ecr_repo: Optional[ElasticContainerRegistryRepository] = values.get("ecr_repo")
        if ecr_repo:
            return ecr_repo.fqn

        return None

    @validator("tags", pre=True, always=True, allow_reuse=True)
    def _set_tags(cls, v: List[str], values: Dict[str, Any]) -> List[str]:
        """Set the value of ``tags``."""
        if v:
            return v

        image: Optional[DockerImage] = values.get("image")
        if image:
            return image.tags

        return ["latest"]


def remove(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image push remove.

    Replicates the functionality of ``docker image push`` CLI command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImageRemoveArgs`.

    """
    args = ImageRemoveArgs.parse_obj({"context": context, **kwargs})
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
