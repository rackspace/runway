"""Docker hook_data object."""
from typing import TYPE_CHECKING, Optional

from ....core.providers.docker import DockerClient
from ....util import MutableMap, cached_property

if TYPE_CHECKING:
    from docker.models.images import Image

    from ...context import Context


class DockerHookData(MutableMap):
    """Docker hook_data object."""

    image = None  # type: Optional["Image"]

    @cached_property
    def client(self):  # type: () -> DockerClient
        """Docker client."""  # pylint: disable=no-self-use
        return DockerClient.from_env()

    def update_context(
        self, context=None
    ):  # type: (Optional["Context"]) -> Optional[DockerHookData]
        """Update context object with new the current DockerHookData."""
        if not context:
            return None
        context.hook_data["docker"] = self
        return self

    @classmethod
    def from_cfngin_context(
        cls, context=None
    ):  # type: (Optional["Context"]) -> DockerHookData
        """Get existing object or create a new one."""
        if context and "docker" in context.hook_data:
            found = context.hook_data["docker"]
            if isinstance(found, cls):
                return found
        new_obj = cls()
        context.hook_data["docker"] = new_obj
        return new_obj
