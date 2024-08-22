"""Customized JSON encoder."""

from __future__ import annotations

import datetime
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from pydantic import BaseModel


class JsonEncoder(json.JSONEncoder):
    """Encode Python objects to JSON data.

    This class can be used with ``json.dumps()`` to handle most data types
    that can occur in responses from AWS.

    Usage:
        >>> json.dumps(data, cls=JsonEncoder)

    """

    def default(self, o: Any) -> dict[Any, Any] | float | list[Any] | str | Any:
        """Encode types not supported by the default JSONEncoder.

        Args:
            o: Object to encode.

        Returns:
            JSON serializable data type.

        Raises:
            TypeError: Object type could not be encoded.

        """
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, BaseModel):
            return o.model_dump()
        if isinstance(o, (Path, SpecifierSet)):
            return str(o)
        if isinstance(o, (set, tuple)):
            return list(o)  # pyright: ignore[reportUnknownArgumentType]
        return super().default(o)
