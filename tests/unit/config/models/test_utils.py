"""Test runway.config.models.utils."""

# pyright: basic
from pathlib import Path
from typing import Any, Optional

import pytest

from runway.config.models.utils import (
    RUNWAY_LOOKUP_STRING_ERROR,
    convert_null_values,
    resolve_path_field,
    validate_string_is_lookup,
)


@pytest.mark.parametrize(
    "provided, expected",
    [
        ("null", None),
        ("none", None),
        ("undefined", None),
        ("None", None),
        ("retain", "retain"),
        ("", ""),
        (True, True),
        (("something",), ("something",)),
        ({"key": "val"}, {"key": "val"}),
        ({}, {}),
        ([], []),
    ],
)
def test_convert_null_values(provided: Any, expected: Any) -> None:
    """Test convert_null_values."""
    assert convert_null_values(provided) == expected


@pytest.mark.parametrize("provided", [None, Path("./")])
def test_resolve_path_field(provided: Optional[Path]) -> None:
    """Test resolve_path_field."""
    if provided is None:
        assert not resolve_path_field(provided)
    else:
        result = resolve_path_field(provided)
        assert result.is_absolute()  # type: ignore
        assert result == provided.resolve()


@pytest.mark.parametrize(
    "provided",
    [
        None,
        {"key", "val"},
        "${env something}",
        "${var ${env DEPLOY_ENVIRONMENT}.something}",
        "${something}",  # not desirable but unavoidable with the current regex
    ],
)
def test_validate_string_is_lookup(provided: Any) -> None:
    """Test validate_string_is_lookup."""
    assert validate_string_is_lookup(provided) == provided


@pytest.mark.parametrize(
    "provided", ["fail", "${fail", "fail}", "fail.${env fail}", "${env fail}.fail"]
)
def test_validate_string_is_lookup_raises(provided: str) -> None:
    """Test validate_string_is_lookup."""
    with pytest.raises(ValueError) as excinfo:
        validate_string_is_lookup(provided)
    assert excinfo.value == RUNWAY_LOOKUP_STRING_ERROR
