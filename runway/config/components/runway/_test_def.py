"""Runway config test definition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ....variables import Variable
from ...models.runway import RunwayTestDefinitionModel, ValidRunwayTestTypeValues
from .base import ConfigComponentDefinition

if TYPE_CHECKING:
    from typing_extensions import Self


class RunwayTestDefinition(ConfigComponentDefinition[RunwayTestDefinitionModel]):
    """Runway test definition."""

    args: dict[str, Any]
    name: str
    required: bool
    type: ClassVar[ValidRunwayTestTypeValues]

    _supports_vars: tuple[str, ...] = ("args", "required")

    def __init__(self, data: RunwayTestDefinitionModel) -> None:
        """Instantiate class."""
        super().__init__(data)

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
        return cls(RunwayTestDefinitionModel.model_validate(obj))
