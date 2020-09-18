"""Runway config base definition."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from ...._logging import PrefixAdaptor
from ....variables import Variable

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....context import Context
    from ...models.base import ConfigProperty
    from ._variables_def import RunwayVariablesDefinition


class ConfigComponentDefinition:
    """Base class for Runway config components."""

    _data: ConfigProperty
    _pre_process_vars: Tuple[str, ...] = ()
    _supports_vars: Tuple[str, ...] = ()
    _vars: Dict[str, Variable] = {}

    def __init__(self, data: ConfigProperty) -> None:
        """Instantiate class."""
        self._data = data.copy()

        self._vars = {}
        for var in self._supports_vars:
            if self._data[var]:
                self._register_variable(var, self._data[var])

    @property
    def data(self) -> Dict[str, Any]:
        """Return the underlying data as a dict."""
        return self._data.dict()

    def resolve(
        self,
        context: Context,
        *,
        pre_process: bool = False,
        variables: Optional[RunwayVariablesDefinition] = None
    ) -> None:
        """Resolve variables."""
        logger = (
            PrefixAdaptor(getattr(self, "name"), LOGGER)
            if hasattr(self, "name")
            else LOGGER
        )

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

        Called while instantiating the class, this is responsible for initalizing
        fields that support variables.

        It can be overridden by subclasses to alter how the variable are initialized.

        Args:
            var_name: Name of the config field that can contain a variable
                lookup.
            var_value: Literal value supplied in the config to be resolved
                as a variable if it contains a lookup.

        """
        self._vars[var_name] = Variable(
            name=var_name, value=var_value, variable_type="runway"
        )

    def __getitem__(self, key: str):
        """Implement evaluation of self[key]."""
        return self._data[key]

    def __getattr__(self, key: str):
        """Implement evaluation of self.key."""
        return self._data[key]
