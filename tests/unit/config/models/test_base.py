"""Test runway.config.models.base."""

from typing import Any, Optional

import pytest
from pydantic import ValidationError

from runway.config.models.base import ConfigProperty


class BadObject(ConfigProperty):
    """Subclass uses to test a parent class.

    This class contains bad configuration.

    """

    name: str = ("invalid",)  # type: ignore


class GoodObject(ConfigProperty):
    """Subclass used to test a parent class.

    This class contains good configuration.

    """

    name: str
    bool_field: bool = True
    dict_field: dict[str, Any] = {}
    optional_str_field: Optional[str] = None


GoodObject.model_config["extra"] = "forbid"


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
        assert errors[0]["msg"] == "Input should be a valid string"

    def test_validate_assignment(self) -> None:
        """Test Config.validate_assignment."""
        with pytest.raises(ValidationError) as excinfo:
            GoodObject(name="test").name = ("invalid",)  # type: ignore
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["msg"] == "Input should be a valid string"
