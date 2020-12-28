"""Runway & CFNgin config model utilities."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

CFNGIN_LOOKUP_STRING_REGEX = r"^\${.*}$"
RUNWAY_LOOKUP_STRING_ERROR = ValueError("field can only be a string if it's a lookup")
RUNWAY_LOOKUP_STRING_REGEX = r"^\${.*}$"


def convert_null_values(v: Any) -> Any:
    """Convert a "null" string into type(None)."""
    null_strings = ["null", "none", "undefined"]
    return None if isinstance(v, str) and v.lower() in null_strings else v


def resolve_path_field(v: Optional[Path]) -> Optional[Path]:
    """Resolve sys_path."""
    return v.resolve() if v else v


def validate_string_is_lookup(v: Any) -> Any:
    """Validate value against regex if it's a string to ensure its a lookup."""
    if isinstance(v, str) and not re.match(RUNWAY_LOOKUP_STRING_REGEX, v):
        raise RUNWAY_LOOKUP_STRING_ERROR
    return v
