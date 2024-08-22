"""Protocols for structural typing.

For more information on protocols, refer to
`PEP 544 <https://www.python.org/dev/peps/pep-0544/>`__.

"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, overload

from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...context import CfnginContext


_T = TypeVar("_T")


class CfnginHookArgsProtocol(Protocol):
    """Protocol for CFNgin hook arguments class.

    This class defines a structural interface for all CFNgin hook argument
    classes. It is recommended to use the provided base class in place of this
    when authoring a new argument class.

    """

    @overload
    @abstractmethod
    def get(self, __name: str) -> Any | None: ...

    @overload
    @abstractmethod
    def get(self, __name: str, __default: Any | _T) -> Any | _T: ...

    @abstractmethod
    def get(self, __name: str, __default: Any | _T = None) -> Any | _T:
        """Safely get the value of an attribute.

        Args:
            name: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, __name: str) -> bool:  # noqa: D105
        raise NotImplementedError

    @abstractmethod
    def __getattribute__(self, __name: str) -> Any:  # noqa: D105
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, __name: str) -> Any:  # noqa: D105
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, __name: str, _value: Any) -> None:  # noqa: D105
        raise NotImplementedError


@runtime_checkable
class CfnginHookProtocol(Protocol):
    """Protocol for CFNgin hooks.

    This class defines a structural interface for all CFNgin hook classes.
    Classes used for hooks do not need to subclass this hook. They only need to
    implement a similar interface. While not required, it is still acceptable
    to subclass this class for full type checking of a hook class.

    """

    ARGS_PARSER: ClassVar
    """Class used to parse arguments passed to the hook."""

    @abstractmethod
    def __init__(self, context: CfnginContext, **_kwargs: Any) -> None:
        """Structural __init__ method."""
        raise NotImplementedError

    @abstractmethod
    def post_deploy(self) -> Any:
        """Run during the **post_deploy** stage.

        Returns:
            A "truthy" value if the hook was successful or a "falsy" value if the
            hook failed.

        """
        raise NotImplementedError

    @abstractmethod
    def post_destroy(self) -> Any:
        """Run during the **post_destroy** stage.

        Returns:
            A "truthy" value if the hook was successful or a "falsy" value if the
            hook failed.

        """
        raise NotImplementedError

    @abstractmethod
    def pre_deploy(self) -> Any:
        """Run during the **pre_deploy** stage.

        Returns:
            A "truthy" value if the hook was successful or a "falsy" value if the
            hook failed.

        """
        raise NotImplementedError

    @abstractmethod
    def pre_destroy(self) -> Any:
        """Run during the **pre_destroy** stage.

        Returns:
            A "truthy" value if the hook was successful or a "falsy" value if the
            hook failed.

        """
        raise NotImplementedError
