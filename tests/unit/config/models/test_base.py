"""Test runway.config.models.base."""

# pyright: basic
from typing import Any, Dict, Optional

import pytest
from pydantic import Extra, ValidationError

from runway.config.models.base import ConfigProperty


class BadObject(ConfigProperty):
    """Subclass uses to test a parent class.

    This class contains bad configuration.

    """

    name: str = ("invalid",)  # type: ignore

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid


class GoodObject(ConfigProperty):
    """Subclass used to test a parent class.

    This class contains good configuration.

    """

    name: str
    bool_field: bool = True
    dict_field: Dict[str, Any] = {}
    optional_str_field: Optional[str] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid


class TestConfigProperty:
    """Test runway.config.models.base.ConfigProperty."""

    def test_contains(self) -> None:
        """Test __contains__."""
        obj = GoodObject(name="test")
        assert "name" in obj
        assert "missing" not in obj

    def test_get(self) -> None:
        """Test get."""
        obj = GoodObject(name="test")
        assert obj.get("name") == "test"
        assert not obj.get("missing")
        assert obj.get("missing", "default") == "default"

    def test_getitem(self) -> None:
        """Test __getitem__."""
        assert GoodObject(name="test")["name"] == "test"

    def test_setitem(self) -> None:
        """Test __setitem__."""
        obj = GoodObject(name="test")
        assert obj.name == "test"
        obj["name"] = "new"
        assert obj.name == "new"

    def test_validate_all(self) -> None:
        """Test Config.validate_all."""
        with pytest.raises(ValidationError) as excinfo:
            BadObject()
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["msg"] == "str type expected"

    def test_validate_assignment(self) -> None:
        """Test Config.validate_assignment."""
        with pytest.raises(ValidationError) as excinfo:
            obj = GoodObject(name="test")
            obj.name = ("invalid",)  # type: ignore
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["msg"] == "str type expected"
