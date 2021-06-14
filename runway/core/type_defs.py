"""Type definitions."""
from __future__ import annotations

from typing_extensions import Literal

RunwayActionTypeDef = Literal["deploy", "destroy", "init", "plan", "test"]
