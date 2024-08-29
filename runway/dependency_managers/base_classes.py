"""Base classes for dependency managers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from ..compat import cached_property
from ..mixins import CliInterfaceMixin

if TYPE_CHECKING:
    from _typeshed import StrPath

    from ..context import CfnginContext, RunwayContext
    from ..utils import Version


class DependencyManager(CliInterfaceMixin):
    """Dependency manager for the AWS Lambda runtime.

    Dependency managers are interfaced with via subprocess to ensure that the
    correct version is being used. This is primarily target at Python
    dependency manager that we could import and use directly.

    """

    CONFIG_FILES: ClassVar[tuple[str, ...]]
    """Configuration files used by the dependency manager."""

    def __init__(self, context: CfnginContext | RunwayContext, cwd: StrPath) -> None:
        """Instantiate class.

        Args:
            context: CFNgin or Runway context object.
            cwd: Working directory where commands will be run.

        """
        self.ctx = context
        self.cwd = cwd if isinstance(cwd, Path) else Path(cwd)

    @cached_property
    def version(self) -> Version:
        """Get executable version."""
        raise NotImplementedError

    @classmethod
    def dir_is_project(cls, directory: StrPath, **__kwargs: Any) -> bool:
        """Determine if the directory contains a project for this dependency manager.

        Args:
            directory: Directory to check.

        """
        raise NotImplementedError
