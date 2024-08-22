"""Docker image remove hook.

Replicates the functionality of the ``docker image remove`` CLI command.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

from docker.errors import ImageNotFound
from pydantic import ConfigDict, Field, field_validator

from .....context import CfnginContext
from .....utils import BaseModel
from ..data_models import (
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from ..hook_data import DockerHookData

if TYPE_CHECKING:
    from pydantic import ValidationInfo

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImageRemoveArgs(BaseModel):
    """Args passed to image.remove."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ctx: Annotated[CfnginContext | None, Field(alias="context", exclude=True)] = None

    ecr_repo: ElasticContainerRegistryRepository | None = None  # depends on ctx
    """AWS Elastic Container Registry repository information.
    Providing this will automatically construct the repo URI.
    If provided, do not provide ``repo``.

    If using a private registry, only ``repo_name`` is required.
    If using a public registry, ``repo_name`` and ``registry_alias``.

    """

    force: bool = False
    """Whether to force the removal of the image."""

    image: DockerImage | None = None
    """Image to push."""

    noprune: bool = False
    """Whether to delete untagged parents."""

    repo: Annotated[str | None, Field(validate_default=True)] = None  # depends on ecr_repo & image
    """URI of a non Docker Hub repository where the image will be stored."""

    tags: Annotated[list[str], Field(validate_default=True)] = []
    """List of tags to apply to the image."""

    @field_validator("ecr_repo", mode="before")
    @classmethod
    def _set_ecr_repo(cls, v: Any, info: ValidationInfo) -> Any:
        """Set the value of ``ecr_repo``."""
        if v and isinstance(v, dict):
            return ElasticContainerRegistryRepository.model_validate(
                {
                    "repo_name": v.get("repo_name"),
                    "registry": ElasticContainerRegistry.model_validate(
                        {
                            "account_id": v.get("account_id"),
                            "alias": v.get("registry_alias"),
                            "aws_region": v.get("aws_region"),
                            "context": info.data.get("context"),
                        }
                    ),
                }
            )
        return v

    @field_validator("repo", mode="before")
    @classmethod
    def _set_repo(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Set the value of ``repo``."""
        if v:
            return v

        image: DockerImage | None = info.data.get("image")
        if image:
            return image.repo

        ecr_repo: ElasticContainerRegistryRepository | None = info.data.get("ecr_repo")
        if ecr_repo:
            return ecr_repo.fqn

        return None

    @field_validator("tags", mode="before")
    @classmethod
    def _set_tags(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Set the value of ``tags``."""
        if v:
            return v

        image: DockerImage | None = info.data.get("image")
        if image:
            return image.tags

        return ["latest"]


def remove(*, context: CfnginContext, **kwargs: Any) -> DockerHookData:
    """Docker image push remove.

    Replicates the functionality of ``docker image push`` CLI command.

    kwargs are parsed by :class:`~runway.cfngin.hooks.docker.image.ImageRemoveArgs`.

    """
    args = ImageRemoveArgs.model_validate({"context": context, **kwargs})
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
    if (
        docker_hook_data.image
        and kwargs.get("image")
        and kwargs["image"].id == docker_hook_data.image.id
    ):
        docker_hook_data.image = None  # clear out the image that was set
    return docker_hook_data.update_context(context)
