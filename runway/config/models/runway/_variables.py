"""Runway ``variables`` definition model."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from .. import utils
from ..base import ConfigProperty


class RunwayVariablesDefinitionModel(ConfigProperty):
    """A variable definitions for the Runway config file.

    This is used to resolve the ``var`` lookup.

    """

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "description": "A variable definitions for the Runway config file. "
            "This is used to resolve the 'var' lookup.",
        },
        title="Runway Variables Definition",
        validate_default=True,
        validate_assignment=True,
    )

    file_path: Annotated[
        Path | None,
        Field(
            title="Variables File Path",
            description="Explicit path to a variables file that will be loaded and "
            "merged with the variables defined here.",
        ),
    ] = None
    """Explicit path to a variables file that will be loaded and merged with the variables defined here."""

    sys_path: Annotated[
        Path,
        Field(
            description="Directory to use as the root of a relative 'file_path'. "
            "If not provided, the current working directory is used.",
        ),
    ] = "./"  # pyright: ignore[reportAssignmentType]
    """Directory to use as the root of a relative 'file_path'.
    If not provided, the current working directory is used.

    """

    _convert_null_values = field_validator("*")(utils.convert_null_values)
