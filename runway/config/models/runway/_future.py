"""Runway ``future`` definition model."""

from pydantic import ConfigDict

from ..base import ConfigProperty


class RunwayFutureDefinitionModel(ConfigProperty):
    """Enable features/behaviors that will be become standard ahead of their official release."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Enable features/behaviors that will be become standard "
            "ahead of their official release."
        },
        title="Runway Future Definition",
        validate_default=True,
        validate_assignment=True,
    )
