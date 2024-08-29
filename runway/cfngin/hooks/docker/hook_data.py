"""Docker hook_data object."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from docker import DockerClient

from ....compat import cached_property
from ....utils import MutableMap

if TYPE_CHECKING:
    from ....context import CfnginContext
    from .data_models import DockerImage


class DockerHookData(MutableMap):
    """Docker hook_data object."""

    image: DockerImage | None = None

    @cached_property
    def client(self) -> DockerClient:
        """Docker client."""
        return DockerClient.from_env()

    @overload
    def update_context(self, context: CfnginContext = ...) -> DockerHookData: ...

    @overload
    def update_context(self, context: None = ...) -> None: ...

    def update_context(self, context: CfnginContext | None = None) -> DockerHookData | None:
        """Update context object with new the current DockerHookData."""
        if not context:
            return None
        context.hook_data["docker"] = self
        return self

    @classmethod
    def from_cfngin_context(cls, context: CfnginContext) -> DockerHookData:
        """Get existing object or create a new one."""
        if "docker" in context.hook_data:
            found = context.hook_data["docker"]
            if isinstance(found, cls):
                return found
        new_obj = cls()
        context.hook_data["docker"] = new_obj
        return new_obj

    def __bool__(self) -> bool:
        """Implement evaluation of instances as a bool."""
        return True
