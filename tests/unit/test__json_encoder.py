"""Test runway.utils._json_encoder."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from packaging.specifiers import SpecifierSet

from runway.config.models.runway import RunwayAssumeRoleDefinitionModel
from runway.utils import JsonEncoder


class TestJsonEncoder:
    """Test JsonEncoder."""

    @pytest.mark.parametrize(
        "provided, expected",
        [
            (("foo", "bar"), list),
            (Decimal("1.1"), float),
            (Path.cwd() / ".runway", str),
            (RunwayAssumeRoleDefinitionModel(), dict),
            (SpecifierSet("==1.0"), str),
            (datetime.datetime.now(), str),
            ({"foo"}, list),
        ],
    )
    def test_supported_types(self, provided: Any, expected: type) -> None:
        """Test encoding of supported data types."""
        assert isinstance(JsonEncoder().default(provided), expected)

    @pytest.mark.parametrize("provided", [(None)])
    def test_unsupported_types(self, provided: Any) -> None:
        """Test encoding of unsupported data types."""
        with pytest.raises(TypeError):
            assert not JsonEncoder().default(provided)
