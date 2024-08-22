"""Runway config module definition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....variables import Variable
from ...models.runway import RunwayModuleDefinitionModel
from .base import ConfigComponentDefinition

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import Self

    from ...models.runway import RunwayEnvironmentsType, RunwayEnvVarsType, RunwayModuleTypeTypeDef


class RunwayModuleDefinition(ConfigComponentDefinition[RunwayModuleDefinitionModel]):
    """Runway module definition."""

    class_path: str | None
    environments: RunwayEnvironmentsType
    env_vars: RunwayEnvVarsType
    name: str
    options: dict[str, Any]
    parameters: dict[str, Any]
    path: str | Path | None
    tags: list[str]
    type: RunwayModuleTypeTypeDef | None

    _supports_vars: tuple[str, ...] = (
        "class_path",
        "env_vars",
        "environments",
        "options",
        "parameters",
        "path",
    )

    def __init__(self, data: RunwayModuleDefinitionModel) -> None:
        """Instantiate class."""
        super().__init__(data)

    @property
    def child_modules(self) -> list[RunwayModuleDefinition]:
        """List of child modules."""
        return [RunwayModuleDefinition(child) for child in self._data.parallel]

    @child_modules.setter
    def child_modules(
        self,
        modules: list[RunwayModuleDefinition | RunwayModuleDefinitionModel],
    ) -> None:
        """Set the value of the property.

        Args:
            modules: A list of modules.

        Raises:
            TypeError: The provided value does not match the required types.

        """
        if not isinstance(modules, list):  # type: ignore
            raise TypeError(f"expected list[RunwayModuleDefinition]; got {type(modules)}")
        sanitized: list[RunwayModuleDefinitionModel] = []
        for i, mod in enumerate(modules):
            if isinstance(mod, RunwayModuleDefinition):
                sanitized.append(RunwayModuleDefinitionModel.model_validate(mod.data))
            elif isinstance(mod, RunwayModuleDefinitionModel):  # type: ignore
                sanitized.append(mod)
            else:
                raise TypeError(
                    f"{self.name}.parallel[{i}] is type {type(mod)}; "
                    "expected type RunwayModuleDefinition or RunwayModuleDefinitionModel"
                )
        self._data.parallel = sanitized

    @property
    def is_parent(self) -> bool:
        """Assess if the modules contains child modules (e.g. run in parallel)."""
        return bool(self._data.parallel)

    @property
    def menu_entry(self) -> str:
        """Return menu entry representation of this module."""
        if self.is_parent:
            return f"{self.name} [{', '.join([c.menu_entry for c in self.child_modules])}]"
        return self.name

    def reverse(self) -> None:
        """Reverse the order of child/parallel modules."""
        self._data.parallel.reverse()

    def _register_variable(self, var_name: str, var_value: Any) -> None:
        """Register a variable.

        Args:
            var_name: Name of the config field that can contain a variable
                lookup.
            var_value: Literal value supplied in the config to be resolved
                as a variable if it contains a lookup.

        """
        self._vars[var_name] = Variable(
            name=f"{self.name}.{var_name}", value=var_value, variable_type="runway"
        )

    @classmethod
    def parse_obj(cls: type[Self], obj: object) -> Self:
        """Parse a python object into this class.

        Args:
            obj: The object to parse.

        """
        return cls(RunwayModuleDefinitionModel.model_validate(obj))
