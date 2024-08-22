"""Runway config base definition."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from ...._logging import PrefixAdaptor
from ....exceptions import UnresolvedVariable
from ....variables import Variable

if TYPE_CHECKING:
    from typing_extensions import Self

    from ...._logging import RunwayLogger
    from ....context import RunwayContext
    from ...models.base import ConfigProperty
    from ._variables_def import RunwayVariablesDefinition

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))

_ConfigPropertyTypeVar = TypeVar("_ConfigPropertyTypeVar", bound="ConfigProperty")


class ConfigComponentDefinition(ABC, Generic[_ConfigPropertyTypeVar]):
    """Base class for Runway config components."""

    _data: _ConfigPropertyTypeVar
    _pre_process_vars: tuple[str, ...] = ()
    _supports_vars: tuple[str, ...] = ()
    _vars: dict[str, Variable] = {}

    def __init__(self, data: _ConfigPropertyTypeVar) -> None:
        """Instantiate class."""
        self._data = data.model_copy(deep=True)

        self._vars = {}
        for var in self._supports_vars:
            if self._data[var]:
                self._register_variable(var, self._data[var])

    @property
    def data(self) -> dict[str, Any]:
        """Return the underlying data as a dict."""
        return self._data.model_dump()

    def get(self, name: str, default: Any = None) -> None:
        """Get a value or return default if it is not found.

        Args:
            name: The value to look for.
            default: Returned if no other value is found.

        """
        return getattr(self, name, default)

    def resolve(
        self,
        context: RunwayContext,
        *,
        pre_process: bool = False,
        variables: RunwayVariablesDefinition | None = None,
    ) -> None:
        """Resolve variables.

        Args:
            context: Runway context object.
            pre_process: Whether to only resolve pre-process fields.
            variables: Object containing values to resolve the ``var`` lookup.

        """
        logger = PrefixAdaptor(self.name, LOGGER) if hasattr(self, "name") else LOGGER

        if pre_process:
            logger.verbose("resolving variables for pre-processing...")
            for field in self._pre_process_vars:
                if field in self._vars:
                    self._vars[field].resolve(context, variables=variables)
                    self._data[field] = self._vars[field].value
            return

        logger.verbose("resolving variables...")
        for field, var in self._vars.items():
            var.resolve(context, variables=variables)
            self._data[field] = var.value

    def _register_variable(self, var_name: str, var_value: Any) -> None:
        """Register a variable.

        Called while instantiating the class, this is responsible for initializing
        fields that support variables.

        It can be overridden by subclasses to alter how the variable are initialized.

        Args:
            var_name: Name of the config field that can contain a variable
                lookup.
            var_value: Literal value supplied in the config to be resolved
                as a variable if it contains a lookup.

        """
        self._vars[var_name] = Variable(name=var_name, value=var_value, variable_type="runway")

    @classmethod
    @abstractmethod
    def parse_obj(cls: type[Self], obj: object) -> Self:
        """Parse a python object into this class.

        Args:
            obj: The object to parse.

        """
        raise NotImplementedError

    def __contains__(self, name: str) -> bool:
        """Implement evaluation of 'in' conditional."""
        if name.startswith("_"):
            return name in self.__dict__
        return self._data.__contains__(name)

    def __getattr__(self, name: str) -> Any:
        """Implement evaluation of self.name.

        Args:
            name: The value to look for.

        Raises:
            AttributeError: Object does not contain an attribute for the
                name provided.
            UnresolvedVariable: The value being access is a variable and it
                has not been resolved yet.

        """
        if name in self._vars and not self._vars[name].resolved:
            raise UnresolvedVariable(self._vars[name])
        if name in super().__getattribute__("_data"):
            return super().__getattribute__("_data").__getitem__(name)
        raise AttributeError(f"{self.__class__.__name__} object has no attribute {name}")

    def __getitem__(self, name: str) -> Any:
        """Implement evaluation of self[name].

        Args:
            name: The value to look for.

        Raises:
            KeyError: Object does not contain a field of the name provided.

        """
        try:
            return self.__getattr__(name)
        except AttributeError as exc:
            raise KeyError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        """Implement evaluation of self.name = value.

        When setting an attribute, the value is set on the underlying data model.
        The exception to this is if the name starts with an underscore.

        Args:
            name: The value to set.
            value: The value to assigned to the field.

        Raises:
            AttributeError: The name being set is a property without a setter.

        """
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, property) and prop.fset:
            prop.fset(self, value)
        elif isinstance(prop, property):
            raise AttributeError(f"setting {name} property is not supported")
        elif name.startswith("_") or name in dir(self):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __setitem__(self, name: str, value: Any) -> None:
        """Implement evaluation of self[name] = value.

        When setting an attribute, the value is set on the underlying data model.
        The exception to this is if the name starts with an underscore.

        Args:
            name: The value to set.
            value: The value to assigned to the field.

        """
        self.__setattr__(name, value)
