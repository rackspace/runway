"""Runway test definition models."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import ConfigDict, Field, field_validator
from typing_extensions import Literal

from .. import utils
from ..base import ConfigProperty

ValidRunwayTestTypeValues = Literal["cfn-lint", "script", "yamllint"]


class RunwayTestDefinitionModel(ConfigProperty):
    """Model for a Runway test definition."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "description": "Tests that can be run via the 'test' command.",
        },
        title="Runway Test Definition",
        use_enum_values=True,
        validate_assignment=True,
        validate_default=True,
    )

    args: Annotated[
        dict[str, Any] | str,
        Field(
            title="Arguments",
            description="Arguments to be passed to the test. Support varies by test type.",
        ),
    ] = {}
    name: Annotated[str, Field(description="Name of the test.")] = "test-name"
    required: Annotated[
        bool | str, Field(description="Whether the test must pass for subsequent tests to be run.")
    ] = False
    type: ValidRunwayTestTypeValues

    # TODO (kyle): add regex to schema
    _validate_string_is_lookup = field_validator("args", "required", mode="before")(
        utils.validate_string_is_lookup
    )
