"""Protocols for structural typing."""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...context import CfnginContext


class CfnginHookArgsProtocol(Protocol):
    """Protocol for CFNgin hook arguments class."""

    @abstractmethod
    def get(self, name: str, default: Any = None) -> Any:
        """Implement evaluation of self.get.

        Args:
            name: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, name: str, value: Any) -> None:
        raise NotImplementedError


@runtime_checkable
class CfnginHookProtocol(Protocol):
    """Protocol for CFNgin hooks."""

    args: CfnginHookArgsProtocol

    @abstractmethod
    def __init__(  # pylint: disable=super-init-not-called
        self, context: CfnginContext, **_kwargs: Any
    ) -> None:
        """Structural __init__ method."""

    @abstractmethod
    def post_deploy(self) -> Any:
        """Run during the **post_deploy** stage."""
        raise NotImplementedError

    @abstractmethod
    def post_destroy(self) -> Any:
        """Run during the **post_destroy** stage."""
        raise NotImplementedError

    @abstractmethod
    def pre_deploy(self) -> Any:
        """Run during the **pre_deploy** stage."""
        raise NotImplementedError

    @abstractmethod
    def pre_destroy(self) -> Any:
        """Run during the **pre_destroy** stage."""
        raise NotImplementedError
