"""Runway Serverless Framework Module options."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Extra

from ...base import ConfigProperty


class RunwayServerlessPromotezipOptionDataModel(ConfigProperty):
    """Model for Runway Serverless module promotezip option."""

    bucketname: Optional[str] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway Serverless Framework Module promotezip option"

    def __bool__(self) -> bool:
        """Evaluate the boolean value of the object instance."""
        return bool(self.dict(exclude_none=True))


class RunwayServerlessModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Serverless Framework Module options."""

    args: List[str] = []
    extend_serverless_yml: Dict[str, Any] = {}
    promotezip: RunwayServerlessPromotezipOptionDataModel = (
        RunwayServerlessPromotezipOptionDataModel()
    )
    skip_npm_ci: bool = False

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway Serverless Framework Module options"
