"""Runway deployment ``region`` definition model."""

from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from .. import utils
from ..base import ConfigProperty


class RunwayDeploymentRegionDefinitionModel(ConfigProperty):
    """Only supports ``parallel`` field."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"parallel": ["us-east-1", "us-east-2"]},
                {"parallel": "${var regions.${env DEPLOY_ENVIRONMENT}}"},
            ],
        },
        title="Runway Deployment.regions Definition",
        validate_default=True,
        validate_assignment=True,
    )

    parallel: Annotated[
        list[str] | str,
        Field(
            title="Parallel Regions",
            description="An array of AWS Regions to process asynchronously. (supports lookups)",
        ),
    ]
    """A list of AWS Regions to process asynchronously. (supports lookups)"""

    _validate_string_is_lookup = field_validator("parallel", mode="before")(
        utils.validate_string_is_lookup
    )
