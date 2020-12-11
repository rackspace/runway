"""Docker image push action.

Replicates the functionality of ``docker image push`` CLI command.

CLI docs: https://docs.docker.com/engine/reference/commandline/image_push/

"""
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from docker.models.images import Image

from .._data_models import BaseModel, ElasticContainerRegistryRepository
from .._hook_data import DockerHookData

if TYPE_CHECKING:
    from ....context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


class ImagePushArgs(BaseModel):
    """Args passed to image.push."""

    repo: Optional[str]
    tags: List[str]

    def __init__(
        self,
        ecr_repo=None,  # type: Optional[Dict[str, Any]]
        image=None,  # type: Optional[Image]
        repo=None,  # type: Optional[str]
        tags=None,  # type: Optional[List[str]]
        **kwargs,  # type: Any
    ):  # type: (...) -> None
        """Instantiate class."""
        self.repo = self.determine_repo(
            context=kwargs.get("context"), ecr_repo=ecr_repo, image=image, repo=repo
        )
        if isinstance(image, Image) and not tags:
            tags = [tag.rsplit(":", 1)[-1] for tag in image.tags]
        self.tags = self._validate_list_str(tags or ["latest"], required=True)

    @staticmethod
    def determine_repo(
        context=None,  # type: Optional["Context"]
        ecr_repo=None,  # type: Optional[Dict[str, Optional[str]]]
        image=None,  # type: Optional[Image]
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
        if isinstance(image, Image):
            return image.attrs["RepoTags"][0].rsplit(":", 1)[0]
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
