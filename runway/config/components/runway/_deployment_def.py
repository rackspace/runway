"""Runway config deployment definition."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from ....variables import Variable
from ...models.runway import RunwayDeploymentDefinitionModel
from ._base import ConfigComponentDefinition
from ._module_def import RunwayModuleDefinition

if TYPE_CHECKING:
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
    _reverse: bool = False
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
    def modules(self) -> List[RunwayModuleDefinition]:
        """List of Runway modules."""
        if self._data.modules and not isinstance(
            self._data.modules[0], RunwayModuleDefinition
        ):
            self._data.modules = [
                RunwayModuleDefinition(module) for module in self._data.modules
            ]
        return self._data.modules

    def reverse(self):
        """Reverse the order of modules and regions."""
        self._reverse = not self._reverse
        self.modules.reverse()

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
    def parse_obj(
        cls, obj: Union[Dict[str, Any], List[Any]]
    ) -> Union[RunwayDeploymentDefinition, List[RunwayDeploymentDefinition]]:
        """Parse a python object."""
        if isinstance(obj, dict):
            return cls(RunwayDeploymentDefinitionModel.parse_obj(obj))
        if isinstance(obj, list):
            return [cls(RunwayDeploymentDefinitionModel.parse_obj(o)) for o in obj]
        raise TypeError(f"{type(obj)}; expected type dict or list")
