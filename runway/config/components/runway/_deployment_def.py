"""Runway config deployment definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, overload

from ....exceptions import UnresolvedVariable
from ....variables import Variable
from ...models.runway import RunwayDeploymentDefinitionModel, RunwayModuleDefinitionModel
from ._module_def import RunwayModuleDefinition
from .base import ConfigComponentDefinition

if TYPE_CHECKING:
    from typing_extensions import Self

    from ...models.base import ConfigProperty
    from ...models.runway import (
        RunwayAssumeRoleDefinitionModel,
        RunwayEnvironmentsType,
        RunwayEnvVarsType,
    )

LOGGER = logging.getLogger(__name__.replace("._", "."))


class RunwayDeploymentDefinition(ConfigComponentDefinition[RunwayDeploymentDefinitionModel]):
    """Runway deployment definition."""

    account_alias: str | None
    account_id: str | None
    assume_role: RunwayAssumeRoleDefinitionModel
    environments: RunwayEnvironmentsType
    env_vars: RunwayEnvVarsType
    module_options: dict[str, Any]
    name: str
    parallel_regions: list[str]
    parameters: dict[str, Any]
    regions: list[str]

    _pre_process_vars: tuple[str, ...] = (
        "account_alias",
        "account_id",
        "assume_role",
        "env_vars",
        "regions",
    )
    _supports_vars: tuple[str, ...] = (
        "account_alias",
        "account_id",
        "assume_role",
        "env_vars",
        "environments",
        "module_options",
        "regions",
        "parallel_regions",
        "parameters",
    )

    def __init__(self, data: RunwayDeploymentDefinitionModel) -> None:
        """Instantiate class."""
        super().__init__(data)

    @property
    def menu_entry(self) -> str:
        """Return menu entry representation of this deployment."""
        try:
            regions = self.regions or self.parallel_regions
        except UnresolvedVariable as err:
            LOGGER.debug(
                "attempted to use variable %s before it was resolved; "
                "using literal value in menu entry",
                err.variable.name,
            )
            regions = self._data.regions or self._data.parallel_regions
        return (
            f"{self.name} - {', '.join(module.name for module in self.modules)} "
            f"({', '.join(regions if isinstance(regions, list) else [regions])})"
        )

    @property
    def modules(self) -> list[RunwayModuleDefinition]:
        """List of Runway modules."""
        return [RunwayModuleDefinition(module) for module in self._data.modules]

    @modules.setter
    def modules(self, modules: list[RunwayModuleDefinition]) -> None:
        """Set the value of the property.

        Args:
            modules: A list of modules.

        Raises:
            TypeError: The provided value does not match the required types.

        """
        if not all(isinstance(i, RunwayModuleDefinition) for i in modules):  # type: ignore
            raise TypeError("modules must be type list[RunwayModuleDefinition]")
        self._data.modules = [
            RunwayModuleDefinitionModel.model_validate(mod.data) for mod in modules
        ]

    def reverse(self) -> None:
        """Reverse the order of modules and regions."""
        self._data.modules.reverse()
        for mod in self._data.modules:
            mod.parallel.reverse()
        for prop in [self._data.parallel_regions, self._data.regions]:
            if isinstance(prop, list):
                prop.reverse()

    def set_modules(
        self, modules: list[RunwayModuleDefinition | RunwayModuleDefinitionModel]
    ) -> None:
        """Set the value of modules.

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
                    f"{self.name}.modules[{i}] is type {type(mod)}; "
                    "expected type RunwayModuleDefinition or RunwayModuleDefinitionModel"
                )
        self._data.modules = sanitized

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

    @overload
    @classmethod
    def parse_obj(cls: type[Self], obj: list[dict[str, Any]]) -> list[Self]: ...

    @overload
    @classmethod
    def parse_obj(
        cls: type[Self],
        obj: list[ConfigProperty] | set[ConfigProperty] | tuple[ConfigProperty, ...],
    ) -> list[Self]: ...

    @overload
    @classmethod
    def parse_obj(cls: type[Self], obj: dict[str, Any] | ConfigProperty) -> Self: ...

    @classmethod
    def parse_obj(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls: type[Self], obj: Any
    ) -> Self | list[Self]:
        """Parse a python object into this class.

        Args:
            obj: The object to parse.

        """
        if isinstance(obj, (list, set, tuple)):
            return [cls(RunwayDeploymentDefinitionModel.parse_obj(o)) for o in obj]  # type: ignore
        return cls(RunwayDeploymentDefinitionModel.model_validate(obj))
