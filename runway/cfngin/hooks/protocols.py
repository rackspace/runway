"""Protocols for structural typing.

For more information on protocols, refer to
`PEP 544 <https://www.python.org/dev/peps/pep-0544/>`__.

"""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union, overload

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
    def get(self, _name: str) -> Optional[Any]:
        ...

    @overload
    @abstractmethod
    def get(self, _name: str, default: Union[Any, _T]) -> Union[Any, _T]:
        ...

    @abstractmethod
    def get(self, _name: str, default: Union[Any, _T] = None) -> Union[Any, _T]:
        """Safely get the value of an attribute.

        Args:
            name: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, _name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __getattribute__(self, _name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, _name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, _name: str, _value: Any) -> None:
        raise NotImplementedError


@runtime_checkable
class CfnginHookProtocol(Protocol):
    """Protocol for CFNgin hooks.

    This class defines a structural interface for all CFNgin hook classes.
    Classes used for hooks do not need to subclass this hook. They only need to
    implement a similar interface. While not required, it is still acceptable
    to subclass this class for full type checking of a hook class.

    """

    args: CfnginHookArgsProtocol

    @abstractmethod
    def __init__(  # pylint: disable=super-init-not-called
        self, context: CfnginContext, **_kwargs: Any
    ) -> None:
        """Structural __init__ method.

        This should not be called. Pylint will erroneously warn about
        "super-init-not-called" if using this class as a subclass. This should
        be disabled in-line until the bug reports for this issue is resolved.

        """
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
