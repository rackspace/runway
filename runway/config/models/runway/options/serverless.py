"""Runway Serverless Framework Module options."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from ...base import ConfigProperty


class RunwayServerlessPromotezipOptionDataModel(ConfigProperty):
    """Model for Runway Serverless module promotezip option."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway Serverless Framework Module promotezip option",
        validate_default=True,
        validate_assignment=True,
    )

    bucketname: str | None = None

    def __bool__(self) -> bool:
        """Evaluate the boolean value of the object instance."""
        return bool(self.model_dump(exclude_none=True))


class RunwayServerlessModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Serverless Framework Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway Serverless Framework Module options",
        validate_default=True,
        validate_assignment=True,
    )

    args: list[str] = []
    extend_serverless_yml: dict[str, Any] = {}
    promotezip: RunwayServerlessPromotezipOptionDataModel = (
        RunwayServerlessPromotezipOptionDataModel()
    )
    skip_npm_ci: bool = False
