"""Runway config variables definition."""
from __future__ import annotations

import logging
import sys
from typing import Any, Dict

import yaml

from ....util import MutableMap
from ...models.runway import RunwayVariablesDefinitionModel

LOGGER = logging.getLogger(__name__.replace("._", "."))


class RunwayVariablesDefinition(MutableMap):
    """Runway variables definition."""

    default_names = ["runway.variables.yml", "runway.variables.yaml"]

    def __init__(self, data: RunwayVariablesDefinitionModel) -> None:
        """Instantiate class."""
        self._file_path = data.file_path
        self._sys_path = data.sys_path
        data = RunwayVariablesDefinitionModel(**{**data.dict(), **self.__load_file()})
        super().__init__(**data.dict(exclude={"file_path", "sys_path"}))

    def __load_file(self) -> Dict[str, Any]:
        """Load a variables file."""
        if self._file_path:
            if self._file_path.is_file():
                return yaml.safe_load(self._file_path.read_text())
            LOGGER.error(
                'provided variables file "%s" could not be found', self._file_path
            )
            sys.exit(1)

        for name in self.default_names:
            test_path = self._sys_path / name
            LOGGER.debug("looking for variables file: %s", test_path)
            if test_path.is_file():
                LOGGER.verbose("found variables file: %s", test_path)
                return yaml.safe_load(test_path.read_text())

        LOGGER.info(
            "could not find %s in the current directory; continuing without a variables file",
            " or ".join(self.default_names),
        )
        return {}
