"""Runway ``assume_role`` definition model."""

from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from .. import utils
from ..base import ConfigProperty
from ..utils import RUNWAY_LOOKUP_STRING_REGEX


class RunwayAssumeRoleDefinitionModel(ConfigProperty):
    """Used to defined a role to assume while Runway is processing each module."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"arn": "arn:aws:iam::123456789012:role/name"},
                {
                    "arn": "${var role_arn.${env DEPLOY_ENVIRONMENT}}",
                    "duration": 9001,
                    "post_deploy_env_revert": True,
                    "session_name": "runway-example",
                },
            ],
        },
        title="Runway Deployment.assume_role Definition",
        validate_default=True,
        validate_assignment=True,
    )

    arn: Annotated[
        str | None,
        Field(description="The ARN of the AWS IAM role to be assumed. (supports lookups)"),
    ] = None
    """The ARN of the AWS IAM role to be assumed. (supports lookups)"""

    duration: (
        Annotated[
            int,
            Field(
                description="The duration, in seconds, of the role session. (supports lookups)",
                ge=900,
                le=43200,
            ),
        ]
        | Annotated[str, Field(pattern=RUNWAY_LOOKUP_STRING_REGEX)]
    ) = 3600
    """The duration, in seconds, of the role session. (supports lookups)"""

    post_deploy_env_revert: Annotated[
        bool,
        Field(
            title="Post Deployment Environment Revert",
            description="Revert the credentials stored in environment variables to "
            "what they were prior to execution after the deployment finished processing. "
            "(supports lookups)",
        ),
    ] = False
    """Revert the credentials stored in environment variables to what they were
    prior to execution after the deployment finished processing. (supports lookups)

    """

    session_name: Annotated[
        str,
        Field(
            description="An identifier for the assumed role session. (supports lookups)",
        ),
    ] = "runway"
    """An identifier for the assumed role session. (supports lookups)"""

    @field_validator("arn")
    @classmethod
    def _convert_arn_null_value(cls, v: str | None) -> str | None:
        """Convert a "nul" string into type(None)."""
        null_strings = ["null", "none", "undefined"]
        return None if isinstance(v, str) and v.lower() in null_strings else v

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, v: int | str) -> int | str:
        """Validate duration is within the range allowed by AWS."""
        if isinstance(v, str):
            return v
        if v < 900:
            raise ValueError("duration must be greater than or equal to 900")
        if v > 43_200:
            raise ValueError("duration must be less than or equal to 43,200")
        return v

    _validate_string_is_lookup = field_validator("duration", mode="before")(
        utils.validate_string_is_lookup
    )
