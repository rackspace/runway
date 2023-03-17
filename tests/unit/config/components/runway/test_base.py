"""Test runway.config.components.runway.base."""
# pylint: disable=protected-access
# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from mock import MagicMock, call
from pydantic import Extra

from runway.config.components.runway import RunwayVariablesDefinition
from runway.config.components.runway.base import ConfigComponentDefinition
from runway.config.models.base import ConfigProperty
from runway.exceptions import UnresolvedVariable

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from ....factories import MockRunwayContext


class SampleConfigProperty(ConfigProperty):
    """Data class for SampleConfigComponentDefinition."""

    name: str = "test"
    var_attr: Any = None
    var_attr_pre: Any = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.allow
        validate_all = False
        validate_assignment = False


class SampleConfigComponentDefinition(ConfigComponentDefinition):
    """Subclass used to test a parent class."""

    name: str
    var_attr: Any
    var_attr_pre: Any

    _data: SampleConfigProperty
    _pre_process_vars = ("var_attr_pre",)
    _supports_vars = ("var_attr", "var_attr_pre")

    def __init__(self, data: SampleConfigProperty) -> None:
        """Instantiate class."""
        super().__init__(data)

    @property
    def can_set(self) -> str:
        """Property with a setter."""
        return f"{self.name}.can_set"

    @can_set.setter
    def can_set(self, value: str) -> None:
        """Property setter."""
        self._data.name = value

    @property
    def no_set(self) -> str:
        """Property without a setter."""
        return "no setter"

    @classmethod
    def parse_obj(cls, obj: Any) -> SampleConfigComponentDefinition:
        """Parse a python object into this class.

        Args:
            obj: The object to parse.

        """
        return cls(SampleConfigProperty.parse_obj(obj))


class TestConfigComponentDefinition:
    """Test runway.config.components.runway.base.ConfigComponentDefinition."""

    VARIABLES = RunwayVariablesDefinition.parse_obj(
        {"key": "val", "test": {"key": "test-val"}}
    )

    def test_contains(self) -> None:
        """Test __contains__."""
        obj = SampleConfigComponentDefinition.parse_obj({})
        assert "name" in obj
        assert "_data" in obj
        assert "missing" not in obj
        assert "_missing" not in obj

    def test_default(self) -> None:
        """Test default setup."""
        data = SampleConfigProperty()
        obj = SampleConfigComponentDefinition(data)
        assert obj._data == data
        assert obj.data == data.dict()
        assert not obj._vars and isinstance(obj._vars, dict)

    def test_get(self) -> None:
        """Test get."""
        obj = SampleConfigComponentDefinition.parse_obj({"name": "test"})
        assert obj.get("name") == "test"
        assert not obj.get("missing")
        assert obj.get("missing", "default") == "default"

    def test_getattr(self, runway_context: MockRunwayContext) -> None:
        """Test __getattr__."""
        data = SampleConfigProperty(
            var_attr="${var ${env DEPLOY_ENVIRONMENT}.key}", var_attr_pre="${var key}"
        )
        obj = SampleConfigComponentDefinition(data)
        assert not obj.resolve(
            runway_context, pre_process=True, variables=self.VARIABLES
        )

        assert obj.var_attr_pre == self.VARIABLES["key"]
        with pytest.raises(UnresolvedVariable):
            assert not obj.var_attr
        with pytest.raises(AttributeError):
            assert not obj.missing

    def test_getitem(self, monkeypatch: MonkeyPatch) -> None:
        """Test __getitem__."""
        mock_getattr = MagicMock(side_effect=["val", AttributeError])
        monkeypatch.setattr(
            SampleConfigComponentDefinition, "__getattr__", mock_getattr
        )
        obj = SampleConfigComponentDefinition.parse_obj({})

        assert obj["key"] == "val"
        with pytest.raises(KeyError):
            assert not obj["key"]
        mock_getattr.assert_has_calls([call("key"), call("key")])

    def test_register_variable(self) -> None:
        """Test _register_variable."""
        data = SampleConfigProperty(var_attr="something", var_attr_pre="literal")
        obj = SampleConfigComponentDefinition(data)

        assert len(obj._vars) == 2

        assert obj._vars["var_attr"].name == "var_attr"
        assert obj._vars["var_attr"].resolved
        assert obj._vars["var_attr"].value == "something"
        assert obj.var_attr == obj._vars["var_attr"].value

        assert obj._vars["var_attr_pre"].name == "var_attr_pre"
        assert obj._vars["var_attr_pre"].resolved
        assert obj._vars["var_attr_pre"].value == "literal"
        assert obj.var_attr_pre == obj._vars["var_attr_pre"].value

    def test_resolve(self, runway_context: MockRunwayContext) -> None:
        """Test resolve."""
        data = SampleConfigProperty(
            var_attr="${var ${env DEPLOY_ENVIRONMENT}.key}", var_attr_pre="${var key}"
        )
        obj = SampleConfigComponentDefinition(data)
        assert not obj.resolve(runway_context, variables=self.VARIABLES)

        assert obj._vars["var_attr"].resolved
        assert obj.var_attr != data.var_attr
        assert obj.var_attr == self.VARIABLES["test"]["key"]

        assert obj._vars["var_attr_pre"].resolved
        assert obj.var_attr_pre != data.var_attr_pre
        assert obj.var_attr_pre == self.VARIABLES["key"]

    def test_resolve_pre_process(self, runway_context: MockRunwayContext) -> None:
        """Test resolve pre-process."""
        data = SampleConfigProperty(
            var_attr="${var ${env DEPLOY_ENVIRONMENT}.key}", var_attr_pre="${var key}"
        )
        obj = SampleConfigComponentDefinition(data)
        assert not obj.resolve(
            runway_context, pre_process=True, variables=self.VARIABLES
        )

        assert not obj._vars["var_attr"].resolved
        with pytest.raises(UnresolvedVariable):
            assert not obj.var_attr

        assert obj._vars["var_attr_pre"].resolved
        assert obj.var_attr_pre != data.var_attr_pre
        assert obj.var_attr_pre == self.VARIABLES["key"]

    def test_setattr(self) -> None:
        """Test __setattr__."""
        obj = SampleConfigComponentDefinition.parse_obj({})
        assert not obj._data.get("key")
        obj.key = "val"  # pylint: disable=attribute-defined-outside-init
        assert obj._data["key"] == "val"
        assert obj.key == "val"

    def test_setattr_property(self) -> None:
        """Test __setattr__ with a property."""
        obj = SampleConfigComponentDefinition.parse_obj({"name": "test"})
        with pytest.raises(AttributeError):
            obj.no_set = "new value"  # type: ignore
        assert obj.can_set == "test.can_set"
        obj.can_set = "new"
        assert obj.can_set == "new.can_set"

    def test_setattr_underscore(self) -> None:
        """Test __setattr__ underscore."""
        obj = SampleConfigComponentDefinition.parse_obj({})
        obj._key = "_val"  # pylint: disable=attribute-defined-outside-init
        assert "_key" not in obj._data
        assert obj._key == "_val"

    def test_setitem(self) -> None:
        """Test __setitem__."""
        obj = SampleConfigComponentDefinition.parse_obj({})
        assert not obj._data.get("key")
        obj["key"] = "val"
        assert obj._data["key"] == "val"
        assert obj["key"] == "val"
