"""Runway config deployment definition."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union, overload

from ....variables import Variable
from ...models.runway import (
    RunwayDeploymentDefinitionModel,
    RunwayModuleDefinitionModel,
)
from ._module_def import RunwayModuleDefinition
from .base import ConfigComponentDefinition

if TYPE_CHECKING:
    from ...models.base import ConfigProperty
    from ...models.runway import (
        RunwayAssumeRoleDefinitionModel,
        RunwayEnvironmentsType,
        RunwayEnvVarsType,
    )


class RunwayDeploymentDefinition(ConfigComponentDefinition):
    """Runway deployment definition."""

    account_alias: Dict[str, str]
    account_id: Dict[str, str]
    assume_role: RunwayAssumeRoleDefinitionModel
    environments: RunwayEnvironmentsType
    env_vars: RunwayEnvVarsType
    module_options: Dict[str, Any]
    name: str
    parallel_regions: List[str]
    parameters: Dict[str, Any]
    regions: List[str]  # TODO add support for regions.parallel

    _data: RunwayDeploymentDefinitionModel
    _pre_process_vars: Tuple[str, ...] = (
        "account_alias",
        "account_id",
        "assume_role",
        "env_vars",
        "regions",
    )
    _supports_vars: Tuple[str, ...] = (
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
        return "{name} - {modules} ({regions})".format(
            name=self.name,
            modules=", ".join([module.name for module in self.modules]),
            regions=", ".join(self.regions or self.parallel_regions),
        )

    @property
    def modules(self) -> List[RunwayModuleDefinition]:
        """List of Runway modules."""
        return [RunwayModuleDefinition(module) for module in self._data.modules]

    @modules.setter
    def modules(
        self, modules: List[Union[RunwayModuleDefinition, RunwayModuleDefinitionModel]]
    ) -> None:
        """Set the value of the property.

        Args:
            modules: A list of modules.

        Raises:
            TypeError: The provided value does not match the required types.

        """
        if not isinstance(modules, list):
            raise TypeError(
                f"expected List[RunwayModuleDefinition]; got {type(modules)}"
            )
        sanitized = []
        for i, mod in enumerate(modules):
            if isinstance(mod, RunwayModuleDefinition):
                sanitized.append(RunwayModuleDefinitionModel.parse_obj(mod.data))
            elif isinstance(mod, RunwayModuleDefinitionModel):
                sanitized.append(mod)
            else:
                raise TypeError(
                    f"{self.name}.modules[{i}] is type {type(mod)}; "
                    "expected type RunwayModuleDefinition or RunwayModuleDefinitionModel"
                )
        self._data.modules = sanitized

    def reverse(self):
        """Reverse the order of modules and regions."""
        self._data.modules.reverse()
        for mod in self._data.modules:
            mod.parallel.reverse()
        self._data.parallel_regions.reverse()
        self._data.regions.reverse()

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
    def parse_obj(  # noqa
        cls, obj: Union[list, set, tuple]
    ) -> List[RunwayDeploymentDefinition]:
        ...  # cov: ignore

    @overload
    @classmethod
    def parse_obj(  # noqa
        cls, obj: Union[Dict[str, Any], ConfigProperty]
    ) -> RunwayDeploymentDefinition:
        ...  # cov: ignore

    @classmethod
    def parse_obj(
        cls, obj: Any
    ) -> Union[RunwayDeploymentDefinition, List[RunwayDeploymentDefinition]]:
        """Parse a python object into this class.

        Args:
            obj: The object to parse.

        """
        if isinstance(obj, (list, set, tuple)):
            return [cls(RunwayDeploymentDefinitionModel.parse_obj(o)) for o in obj]
        return cls(RunwayDeploymentDefinitionModel.parse_obj(obj))
