"""Test runway.utils.pydantic_validators._lax_str."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from runway.utils.pydantic_validators._lax_str import LaxStr


class SomeEnum(str, Enum):
    """Enum for testing."""

    FOO = "foo"


class Model(BaseModel):
    """Model used for testing."""

    test: Annotated[str | None, LaxStr]


@pytest.mark.parametrize(
    "provided, expected",
    [
        ("foo", "foo"),
        (5, "5"),
        (1.0, "1.0"),
        (Decimal("1.0"), "1.0"),
        (SomeEnum.FOO, "foo"),
        (b"foo", "foo"),
        (None, None),
    ],
)
def test__handler(provided: object, expected: str) -> None:
    """Test _handler."""
    assert Model.model_validate({"test": provided}).test == expected


@pytest.mark.parametrize(
    "provided",
    [{"foo": "bar"}, {"foo", "bar"}, ["foo", "bar"], ("foo", "bar")],
)
def test_raise_validation_error(provided: object) -> None:
    """Test _handler unconverted."""
    with pytest.raises(ValidationError):
        Model.model_validate({"test": provided})
