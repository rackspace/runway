"""Runway config module definition."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ....variables import Variable
from ._base import ConfigComponentDefinition

if TYPE_CHECKING:
    from ...models.runway import (
        RunwayEnvironmentsType,
        RunwayEnvVarsType,
        RunwayModuleDefinitionModel,
    )


class RunwayModuleDefinition(ConfigComponentDefinition):
    """Runway module definition."""

    environments: RunwayEnvironmentsType
    env_vars: RunwayEnvVarsType
    name: str
    options: Dict[str, Any]
    parameters: Dict[str, Any]
    tags: List[str]
    type: Optional[str]  # TODO add enum

    _data: RunwayModuleDefinitionModel
    _supports_vars: Tuple[str, ...] = (
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
    def child_modules(self) -> List[RunwayModuleDefinition]:
        """List of child modules."""
        if self._data.parallel and not isinstance(
            self._data.parallel[0], RunwayModuleDefinition
        ):
            self._data.parallel = [
                RunwayModuleDefinition(child) for child in self._data.parallel
            ]
        return self._data.parallel

    @property
    def class_path(self) -> Optional[Path]:
        """Path to a class for processing the module."""
        return Path(self._data.class_path).resolve() if self._data.class_path else None

    @property
    def path(self) -> Path:
        """Path to Runway module."""
        if isinstance(self._data.path, str):
            self._data.path = Path(self._data.path).resolve()
        return self._data.path

    @path.setter
    def path(self, value: Path) -> None:
        """Set the value of path."""
        self._data.path = value

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
