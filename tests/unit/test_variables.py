"""Tests for runway.variables."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import MagicMock, call

import pytest
from pydantic import BaseModel

from runway.exceptions import (
    FailedLookup,
    FailedVariableLookup,
    InvalidLookupConcatenation,
    UnknownLookupType,
    UnresolvedVariable,
    UnresolvedVariableValue,
)
from runway.lookups.handlers.base import LookupHandler
from runway.variables import (
    CFNGIN_LOOKUP_HANDLERS,
    RUNWAY_LOOKUP_HANDLERS,
    Variable,
    VariableTypeLiteralTypeDef,
    VariableValue,
    VariableValueConcatenation,
    VariableValueDict,
    VariableValueList,
    VariableValueLiteral,
    VariableValueLookup,
    VariableValuePydanticModel,
    resolve_variables,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from .factories import MockCfnginContext


class ExampleModel(BaseModel):
    """Example model used for testing."""

    test: Any = "val"


class MockLookupHandler(LookupHandler):
    """Mock lookup handler."""

    return_value: ClassVar[Any] = "resolved"
    side_effect: ClassVar[Any | list[Any]] = None

    @classmethod
    def handle(
        cls,
        *__args: Any,
        **__kwargs: Any,
    ) -> Any:
        """Perform the lookup."""
        if cls.side_effect is None:
            return cls.return_value
        if isinstance(cls.side_effect, list):
            return cls._handle_side_effect(cls.side_effect.pop(0))
        return cls._handle_side_effect(cls.side_effect)

    @classmethod
    def _handle_side_effect(cls, side_effect: Any) -> Any:
        """Handle side_effect."""
        if isinstance(side_effect, BaseException):
            raise side_effect
        return side_effect


@pytest.fixture(autouse=True)
def patch_lookups(mocker: MockerFixture) -> None:
    """Patch registered lookups."""
    for registry in [CFNGIN_LOOKUP_HANDLERS, RUNWAY_LOOKUP_HANDLERS]:
        mocker.patch.dict(registry, {"test": MockLookupHandler})


def test_resolve_variables(cfngin_context: MockCfnginContext) -> None:
    """Test resolve_variables."""
    variable = MagicMock()
    assert not resolve_variables([variable], cfngin_context)
    variable.resolve.assert_called_once_with(context=cfngin_context, provider=None)


class TestVariables:
    """Test runway.variables.Variables."""

    def test_dependencies(self, mocker: MockerFixture) -> None:
        """Test dependencies."""
        assert Variable("Param", "val").dependencies == set()
        mocker.patch.object(
            VariableValue, "parse_obj", return_value=MagicMock(dependencies={"test"})
        )
        assert Variable("Param", "val").dependencies == {"test"}

    def test_get(self) -> None:
        """Test get."""
        obj = Variable("Para", {"key": "val"})
        assert obj.get("missing") is None
        assert obj.get("missing", "default") == "default"

    @pytest.mark.parametrize("variable_type", ["cfngin", "runway"])
    def test_init(self, variable_type: VariableTypeLiteralTypeDef) -> None:
        """Test __init__."""
        obj = Variable("Param", "val", variable_type)
        assert obj.name == "Param"
        assert obj.variable_type == variable_type
        assert obj._raw_value == "val"
        assert obj._value.value == "val"
        assert obj._value.variable_type == variable_type

    def test_multiple_lookup_dict(self, mocker: MockerFixture) -> None:
        """Test multiple lookup dict."""
        mocker.patch.object(MockLookupHandler, "side_effect", ["resolved0", "resolved1"])
        value = {
            "something": "${test query0}",
            "other": "${test query1}",
        }
        var = Variable("Param1", value)
        assert isinstance(var._value, VariableValueDict)
        var.resolve(MagicMock(), MagicMock())
        assert var.value == {"something": "resolved0", "other": "resolved1"}

    def test_multiple_lookup_list(self, mocker: MockerFixture) -> None:
        """Test multiple lookup list."""
        mocker.patch.object(MockLookupHandler, "side_effect", ["resolved0", "resolved1"])
        value = [
            "something",
            "${test query0}",
            "${test query1}",
        ]
        var = Variable("Param1", value)
        assert isinstance(var._value, VariableValueList)
        var.resolve(MagicMock(), MagicMock())
        assert var.value == ["something", "resolved0", "resolved1"]

    def test_multiple_lookup_mixed(self) -> None:
        """Test multiple lookup mixed."""
        value = {
            "something": ["${test query}", "other"],
            "here": {
                "other": "${test query}",
                "same": "${test query}",
                "mixed": "something:${test query}",
            },
        }
        var = Variable("Param1", value)
        assert isinstance(var._value, VariableValueDict)
        var.resolve(MagicMock(), MagicMock())
        assert var.value == {
            "something": ["resolved", "other"],
            "here": {
                "other": "resolved",
                "same": "resolved",
                "mixed": "something:resolved",
            },
        }

    def test_multiple_lookup_string(self, mocker: MockerFixture) -> None:
        """Test multiple lookup string."""
        var = Variable("Param1", "url://${test query0}@${test query1}")
        assert isinstance(var._value, VariableValueConcatenation)
        mocker.patch.object(MockLookupHandler, "side_effect", ["resolved0", "resolved1"])
        var.resolve(MagicMock(), MagicMock())
        assert var.resolved is True
        assert var.value == "url://resolved0@resolved1"

    def test_nested_lookups(self, mocker: MockerFixture) -> None:
        """Test nested lookups."""
        context = MagicMock()
        provider = MagicMock()
        mock_handler = mocker.patch.object(
            MockLookupHandler, "handle", side_effect=["resolved0", "resolved1"]
        )
        var = Variable("Param1", "${test ${test query0}.query1}")
        var.resolve(context, provider)
        mock_handler.assert_has_calls(
            [  # type: ignore
                call("query0", context=context, provider=provider, variables=None),
                call(
                    "resolved0.query1",
                    context=context,
                    provider=provider,
                    variables=None,
                ),
            ]
        )
        assert var.value == "resolved1"

    def test_no_lookup_list(self) -> None:
        """Test no lookup list."""
        var = Variable("Param1", ["something", "here"])
        assert isinstance(var._value, VariableValueList)
        assert var.value == ["something", "here"]

    def test_no_lookup_str(self) -> None:
        """Test no lookup str."""
        var = Variable("Param1", "2")
        assert isinstance(var._value, VariableValueLiteral)
        assert var.value == "2"

    @pytest.mark.parametrize("resolved", [False, True])
    def test_resolved(self, mocker: MockerFixture, resolved: bool) -> None:
        """Test resolved."""
        mocker.patch.object(VariableValue, "parse_obj", return_value=MagicMock(resolved=resolved))
        assert Variable("Param", "val").resolved is resolved

    def test_resolve_failed(self, mocker: MockerFixture) -> None:
        """Test resolve FailedLookup."""
        context = MagicMock()
        provider = MagicMock()
        obj = Variable("Param", "val")
        lookup_error = FailedLookup("something", KeyError("cause"))  # type: ignore
        mocker.patch.object(obj._value, "resolve", side_effect=lookup_error)
        with pytest.raises(FailedVariableLookup) as excinfo:
            obj.resolve(context, provider, kwarg="something")
        assert excinfo.value.cause == lookup_error
        assert excinfo.value.variable == obj

    def test___repr__(self) -> None:
        """Test __repr__."""
        assert repr(Variable("Param", "val")) == "Variable[Param=val]"

    def test_resolve(self, mocker: MockerFixture) -> None:
        """Test resolve."""
        context = MagicMock()
        provider = MagicMock()
        obj = Variable("Param", "val")
        mock_resolve = mocker.patch.object(obj._value, "resolve")
        assert not obj.resolve(context, provider, kwarg="something")
        mock_resolve.assert_called_once_with(
            context, provider=provider, variables=None, kwarg="something"
        )

    def test_simple_lookup(self) -> None:
        """Test simple lookup."""
        var = Variable("Param1", "${test query}")
        assert isinstance(var._value, VariableValueLookup)
        var.resolve(MagicMock(), MagicMock())
        assert var.resolved is True
        assert var.value == "resolved"

    def test_value_unresolved(self, mocker: MockerFixture) -> None:
        """Test value UnresolvedVariable."""
        mocker.patch.object(VariableValue, "parse_obj", return_value=MagicMock(value="value"))

    def test_value(self) -> None:
        """Test value."""
        with pytest.raises(UnresolvedVariable):
            Variable("Param", "${test query}").value  # noqa: B018


class TestVariableValue:
    """Test runway.variables.VariableValue."""

    def test___iter__(self) -> None:
        """Test __iter__."""
        with pytest.raises(NotImplementedError):
            iter(VariableValue())

    def test_dependencies(self) -> None:
        """Test dependencies."""
        obj = VariableValue()
        assert obj.dependencies == set()

    def test_parse_obj_dict_empty(self) -> None:
        """Test parse_obj dict empty."""
        assert isinstance(VariableValue.parse_obj({}), VariableValueDict)

    def test_parse_obj_list_empty(self) -> None:
        """Test parse_obj list empty."""
        assert isinstance(VariableValue.parse_obj([]), VariableValueList)

    @pytest.mark.parametrize("value", [False, True])
    def test_parse_obj_literal_bool(self, value: bool) -> None:
        """Test parse_obj literal bool."""
        obj = VariableValue.parse_obj(value)
        assert isinstance(obj, VariableValueLiteral)
        assert obj.value is value

    def test_parse_obj_literal_int(self) -> None:
        """Test parse_obj literal int."""
        obj = VariableValue.parse_obj(13)
        assert isinstance(obj, VariableValueLiteral)
        assert obj.value == 13

    def test_parse_obj_literal_str(self) -> None:
        """Test parse_obj literal str."""
        obj = VariableValue.parse_obj("test")
        assert obj.value == "test"
        assert isinstance(obj, VariableValueLiteral)

    def test_parse_obj_pydantic_model(self) -> None:
        """Test parse_obj pydantic model."""
        assert isinstance(VariableValue.parse_obj(ExampleModel()), VariableValuePydanticModel)

    def test_repr(self) -> None:
        """Test __repr__."""
        with pytest.raises(NotImplementedError):
            repr(VariableValue())

    def test_resolved(self) -> None:
        """Test resolved."""
        with pytest.raises(NotImplementedError):
            VariableValue().resolved  # noqa: B018

    def test_resolve(self, cfngin_context: MockCfnginContext) -> None:
        """Test resolve."""
        assert not VariableValue().resolve(context=cfngin_context)

    def test_simplified(self) -> None:
        """Test simplified."""
        obj = VariableValue()
        assert obj.simplified == obj

    def test_value(self) -> None:
        """Test value."""
        with pytest.raises(NotImplementedError):
            VariableValue().value  # noqa: B018


class TestVariableValueConcatenation:
    """Test runway.variables.VariableValueConcatenation."""

    def test_delitem(self) -> None:
        """Test __delitem__."""
        obj = VariableValueConcatenation(["val0", "val1"])  # type: ignore
        assert "val1" in obj._data
        del obj[1]
        assert "val1" not in obj._data

    def test_dependencies(self) -> None:
        """Test dependencies."""
        data = [MagicMock(dependencies={"test"})]
        obj = VariableValueConcatenation(data)
        assert obj.dependencies == {"test"}

    def test_getitem(self) -> None:
        """Test __getitem__."""
        obj = VariableValueConcatenation(["val0", "val1"])  # type: ignore
        assert obj[1] == "val1"
        assert obj[:2] == ["val0", "val1"]

    def test_init(self) -> None:
        """Test __init__."""
        data = [VariableValueLiteral("test")]
        obj = VariableValueConcatenation(data)
        assert obj._data == data
        assert obj.variable_type == "cfngin"

    def test_iter(self) -> None:
        """Test __iter__."""
        obj = VariableValueConcatenation(["val0", "val1"])  # type: ignore
        assert list(iter(obj)) == ["val0", "val1"]  # type: ignore

    def test_len(self) -> None:
        """Test __len__."""
        obj = VariableValueConcatenation(["val0", "val1"])  # type: ignore
        assert len(obj) == 2  # type: ignore

    def test_repr(self) -> None:
        """Test __repr__."""
        obj = VariableValueConcatenation(["val0", "val1"])  # type: ignore
        assert repr(obj) == "Concatenation['val0', 'val1']"  # type: ignore

    def test_resolved(self) -> None:
        """Test resolved."""
        assert VariableValueConcatenation([MagicMock(resolved=True)]).resolved is True
        assert VariableValueConcatenation([MagicMock(resolved=False)]).resolved is False
        assert (
            VariableValueConcatenation(
                [MagicMock(resolved=True), MagicMock(resolved=False)]
            ).resolved
            is False
        )

    def test_resolve(self, cfngin_context: MockCfnginContext, mocker: MockerFixture) -> None:
        """Test resolve."""
        mock_provider = MagicMock()
        mock_resolve = mocker.patch.object(VariableValueLiteral, "resolve", return_value=None)
        obj = VariableValueConcatenation([VariableValueLiteral("val0")])
        assert not obj.resolve(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},  # type: ignore
            kwarg="test",
        )
        mock_resolve.assert_called_once_with(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},
            kwarg="test",
        )

    def test_setitem(self) -> None:
        """Test __setitem__."""
        obj = VariableValueConcatenation(["test-val0", "test-val1"])  # type: ignore
        obj[0] = "val0"  # type: ignore
        assert obj[0] == "val0"
        obj[:2] = ["val0", "val1"]  # type: ignore
        assert obj[1] == "val1"

    def test_simplified_concat(self) -> None:
        """Test simplified concatenation."""
        assert (
            VariableValueConcatenation(
                [
                    VariableValueLiteral("foo"),
                    VariableValueConcatenation(
                        [VariableValueLiteral("bar"), VariableValueLiteral("foo")]
                    ),
                ]
            ).simplified.value
            == "foobarfoo"
        )

    def test_simplified_list(self) -> None:
        """Test simplified list."""
        assert [
            i.value
            for i in VariableValueConcatenation([VariableValueList(["foo", "bar"])]).simplified
        ] == ["foo", "bar"]

    def test_simplified_literal_bool(self) -> None:
        """Test simplified literal bool."""
        assert VariableValueConcatenation([VariableValueLiteral(True)]).simplified.value is True
        assert VariableValueConcatenation([VariableValueLiteral(False)]).simplified.value is False

    def test_simplified_literal_empty(self) -> None:
        """Test simplified literal empty."""
        assert VariableValueConcatenation([VariableValueLiteral("")]).simplified.value == ""

    def test_simplified_literal_int(self) -> None:
        """Test simplified literal int."""
        assert VariableValueConcatenation([VariableValueLiteral(13)]).simplified.value == 13

    def test_simplified_literal_str(self) -> None:
        """Test simplified literal str."""
        assert VariableValueConcatenation([VariableValueLiteral("foo")]).simplified.value == "foo"
        assert (
            VariableValueConcatenation(
                [VariableValueLiteral("foo"), VariableValueLiteral("bar")]
            ).simplified.value
            == "foobar"
        )

    @pytest.mark.parametrize(
        "variable, expected",
        [
            (
                VariableValueConcatenation(
                    [VariableValueLiteral("foo"), VariableValueLiteral("bar")]
                ),
                "foobar",
            ),
            (
                VariableValueConcatenation(
                    [VariableValueLiteral(13), VariableValueLiteral("/test")]
                ),
                "13/test",
            ),
            (
                VariableValueConcatenation([VariableValueLiteral(5), VariableValueLiteral(13)]),
                "513",
            ),
        ],
    )
    def test_value_multiple(self, expected: str, variable: VariableValueConcatenation[Any]) -> None:
        """Test value multiple."""
        assert variable.value == expected

    def test_value_multiple_raise_concatenation_error(self) -> None:
        """Test value multiple raises InvalidLookupConcatenationError."""
        with pytest.raises(InvalidLookupConcatenation):
            VariableValueConcatenation(  # noqa: B018
                [VariableValueLiteral(True), VariableValueLiteral(VariableValueLiteral)]  # type: ignore
            ).value

    def test_value_single(self) -> None:
        """Test value single."""
        assert VariableValueConcatenation([VariableValueLiteral("foo")]).value == "foo"
        assert VariableValueConcatenation([VariableValueLiteral(13)]).value == 13


class TestVariableValueDict:
    """Test runway.variables.VariableValueDict."""

    def test_delitem(self) -> None:
        """Test __delitem__."""
        obj = VariableValueDict({"key": "val"})
        assert "key" in obj
        del obj["key"]
        assert "key" not in obj

    def test_dependencies(self, mocker: MockerFixture) -> None:
        """Test dependencies."""
        mock_literal = MagicMock(dependencies=set("test"))
        mocker.patch.object(VariableValueDict, "parse_obj", return_value=mock_literal)
        obj = VariableValueDict({"key": "val"})
        assert obj.dependencies == set("test")

    def test_getitem(self, mocker: MockerFixture) -> None:
        """Test __getitem__."""
        mocker.patch.object(VariableValueDict, "parse_obj", return_value="parsed_val")
        obj = VariableValueDict({"key": "val"})
        assert obj["key"] == "parsed_val"

    def test_init(self, mocker: MockerFixture) -> None:
        """Test __init__."""
        mock_parse_obj = mocker.patch.object(
            VariableValueDict, "parse_obj", return_value="parsed_val"
        )
        obj = VariableValueDict({"key": "val"})
        assert obj._data == {"key": mock_parse_obj.return_value}
        mock_parse_obj.assert_called_once_with("val", variable_type="cfngin")
        assert obj.variable_type == "cfngin"

    def test_iter(self) -> None:
        """Test __iter__."""
        obj = VariableValueDict({"key": "val"})
        assert list(iter(obj)) == ["key"]

    def test_len(self) -> None:
        """Test __len__."""
        obj = VariableValueDict({"key0": "val0", "key1": "val1"})
        assert len(obj) == 2

    def test_repr(self) -> None:
        """Test __repr__."""
        obj = VariableValueDict({"key0": "val0", "key1": "val1"})
        assert repr(obj) == "dict[key0=Literal[val0], key1=Literal[val1]]"

    @pytest.mark.parametrize("resolved", [False, True])
    def test_resolved(self, mocker: MockerFixture, resolved: bool) -> None:
        """Test resolved."""
        mock_literal = MagicMock(resolved=resolved)
        mocker.patch.object(VariableValueDict, "parse_obj", return_value=mock_literal)
        obj = VariableValueDict({"key": "val"})
        assert obj.resolved is resolved

    def test_resolve(self, cfngin_context: MockCfnginContext, mocker: MockerFixture) -> None:
        """Test resolve."""
        mock_literal = MagicMock()
        mock_provider = MagicMock()
        mocker.patch.object(VariableValueDict, "parse_obj", return_value=mock_literal)
        obj = VariableValueDict({"key": "val"})
        assert not obj.resolve(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},  # type: ignore
            kwarg="test",
        )
        mock_literal.resolve.assert_called_once_with(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},
            kwarg="test",
        )

    def test_setitem(self, mocker: MockerFixture) -> None:
        """Test __setitem__."""
        mocker.patch.object(VariableValueDict, "parse_obj", return_value="parsed_val")
        obj = VariableValueDict({"key": "val"})
        obj["key"] = "new"  # type: ignore
        assert obj["key"] == "new"

    def test_simplified(self, mocker: MockerFixture) -> None:
        """Test simplified."""
        mock_literal = MagicMock(simplified="simplified")
        mocker.patch.object(VariableValueDict, "parse_obj", return_value=mock_literal)
        obj = VariableValueDict({"key": "val"})
        assert obj.simplified == {"key": "simplified"}

    def test_value(self, mocker: MockerFixture) -> None:
        """Test value."""
        mock_literal = MagicMock(value="value")
        mocker.patch.object(VariableValueDict, "parse_obj", return_value=mock_literal)
        obj = VariableValueDict({"key": "val"})
        assert obj.value == {"key": "value"}


class TestVariableValueList:
    """Test runway.variables.VariableValueList."""

    def test_delitem(self) -> None:
        """Test __delitem__."""
        obj = VariableValueList(["val0", "val1"])
        assert "val1" in [i._data for i in obj]
        del obj[1]
        assert "val1" not in [i._data for i in obj]

    def test_dependencies(self, mocker: MockerFixture) -> None:
        """Test dependencies."""
        mock_literal = MagicMock(dependencies=set("test"))
        mocker.patch.object(VariableValueList, "parse_obj", return_value=mock_literal)
        obj = VariableValueList(["val0"])
        assert obj.dependencies == set("test")

    def test_getitem(self) -> None:
        """Test __getitem__."""
        obj = VariableValueList(["val0", "val1"])
        assert obj[1].value == "val1"
        assert [i.value for i in obj[:2]] == ["val0", "val1"]

    def test_init(self, mocker: MockerFixture) -> None:
        """Test __init__."""
        mock_parse_obj = mocker.patch.object(
            VariableValueList, "parse_obj", return_value="parsed_val"
        )
        obj = VariableValueList(["val"])
        assert obj._data == ["parsed_val"]
        mock_parse_obj.assert_called_once_with("val", variable_type="cfngin")
        assert obj.variable_type == "cfngin"

    def test_insert(self) -> None:
        """Test insert."""
        obj = VariableValueList(["val0", "val1"])
        obj.insert(1, VariableValueLiteral("val2"))
        assert [i.value for i in obj] == ["val0", "val2", "val1"]

    def test_iter(self) -> None:
        """Test __iter__."""
        obj = VariableValueList(["val0", "val1"])
        assert [i.value for i in iter(obj)] == ["val0", "val1"]

    def test_len(self) -> None:
        """Test __len__."""
        obj = VariableValueList(["val0", "val1"])
        assert len(obj) == 2

    def test_repr(self) -> None:
        """Test __repr__."""
        obj = VariableValueList(["val0", "val1"])
        assert repr(obj) == "list[Literal[val0], Literal[val1]]"

    @pytest.mark.parametrize("resolved", [False, True])
    def test_resolved(self, mocker: MockerFixture, resolved: bool) -> None:
        """Test resolved."""
        mock_literal = MagicMock(resolved=resolved)
        mocker.patch.object(VariableValueList, "parse_obj", return_value=mock_literal)
        obj = VariableValueList(["val0"])
        assert obj.resolved is resolved

    def test_resolve(self, cfngin_context: MockCfnginContext, mocker: MockerFixture) -> None:
        """Test resolve."""
        mock_literal = MagicMock()
        mock_provider = MagicMock()
        mocker.patch.object(VariableValueList, "parse_obj", return_value=mock_literal)
        obj = VariableValueList(["val0"])
        assert not obj.resolve(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},  # type: ignore
            kwarg="test",
        )
        mock_literal.resolve.assert_called_once_with(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},
            kwarg="test",
        )

    def test_setitem(self) -> None:
        """Test __setitem__."""
        obj = VariableValueList(["val0", "val1"])
        obj[0] = "val0"  # type: ignore
        assert obj[0] == "val0"
        assert obj[1] != "val1"
        obj[:2] = ["val0", "val1"]  # type: ignore
        assert obj[1] == "val1"

    def test_simplified(self, mocker: MockerFixture) -> None:
        """Test simplified."""
        mock_literal = MagicMock(simplified="simplified")
        mocker.patch.object(VariableValueList, "parse_obj", return_value=mock_literal)
        obj = VariableValueList(["val0"])
        assert obj.simplified == ["simplified"]

    def test_value(self, mocker: MockerFixture) -> None:
        """Test value."""
        mock_literal = MagicMock(value="value")
        mocker.patch.object(VariableValueList, "parse_obj", return_value=mock_literal)
        obj = VariableValueList(["val0"])
        assert obj.value == ["value"]


class TestVariableValueLiteral:
    """Test runway.variables.VariableValueLiteral."""

    @pytest.mark.parametrize("value", [False, True, 13, "test"])
    def test_init(self, value: int | str) -> None:
        """Test __init__."""
        obj = VariableValueLiteral(value)  # type: ignore
        assert obj._data == value

    @pytest.mark.parametrize("value", [False, True, 13, "test"])
    def test_iter(self, value: int | str) -> None:
        """Test __iter__."""
        obj = VariableValueLiteral(value)  # type: ignore
        assert list(iter(obj)) == [obj]  # type: ignore

    @pytest.mark.parametrize("value", [False, True, 13, "test"])
    def test_repr(self, value: int | str) -> None:
        """Test __repr__."""
        obj = VariableValueLiteral(value)  # type: ignore
        assert repr(obj) == f"Literal[{value}]"  # type: ignore

    @pytest.mark.parametrize("value", [False, True, 13, "test"])
    def test_resolved(self, value: int | str) -> None:
        """Test resolved."""
        obj = VariableValueLiteral(value)  # type: ignore
        assert obj.resolved

    @pytest.mark.parametrize("value", [False, True, 13, "test"])
    def test_value(self, value: int | str) -> None:
        """Test value."""
        obj = VariableValueLiteral(value)  # type: ignore
        assert obj.value == value


class TestVariableValueLookup:
    """Test runway.variables.VariableValueLookup."""

    def test_dependencies_no_attr(self) -> None:
        """Test dependencies class has no attr."""

        class FakeLookup:
            """Fake lookup."""

        obj = VariableValueLookup(VariableValueLiteral("test"), "query", FakeLookup)  # type: ignore
        assert obj.dependencies == set()

    def test_dependencies(self, mocker: MockerFixture) -> None:
        """Test dependencies."""
        mocker.patch.object(MockLookupHandler, "dependencies", return_value={"test"})
        obj = VariableValueLookup(VariableValueLiteral("test"), "query", MockLookupHandler)
        assert obj.dependencies == {"test"}

    def test___init___convert_query(self) -> None:
        """Test __init__ convert query."""
        obj = VariableValueLookup(
            VariableValueLiteral("test"), "query", MockLookupHandler, "runway"
        )
        assert isinstance(obj.lookup_query, VariableValueLiteral)
        assert obj.lookup_query.value == "query"

    def test___init___find_handler_cfngin(self, mocker: MockerFixture) -> None:
        """Test __init__ find handler cfngin."""
        mocker.patch.dict(CFNGIN_LOOKUP_HANDLERS, {"test": "success"})
        obj = VariableValueLookup(VariableValueLiteral("test"), VariableValueLiteral("query"))
        assert obj.handler == "success"

    def test___init___find_handler_runway(self, mocker: MockerFixture) -> None:
        """Test __init__ find handler runway."""
        mocker.patch.dict(RUNWAY_LOOKUP_HANDLERS, {"test": "success"})
        obj = VariableValueLookup(
            VariableValueLiteral("test"),
            VariableValueLiteral("query"),
            variable_type="runway",
        )
        assert obj.handler == "success"

    def test___init___find_handler_value_error(self) -> None:
        """Test __init__ fund handler ValueError."""
        with pytest.raises(ValueError, match="Variable type must be one of"):
            VariableValueLookup(
                VariableValueLiteral("test"),
                VariableValueLiteral("query"),
                variable_type="invalid",  # type: ignore
            )

    def test___init___find_handler_unknown_lookup_type(self) -> None:
        """Test __init__ fund handler UnknownLookupType."""
        with pytest.raises(UnknownLookupType):
            VariableValueLookup(
                VariableValueLiteral("invalid"),
                VariableValueLiteral("query"),
            )

    def test___init__(self) -> None:
        """Test __init__."""
        name = VariableValueLiteral("test")
        query = VariableValueLiteral("query")
        obj = VariableValueLookup(name, query, MockLookupHandler, "runway")
        assert obj.handler == MockLookupHandler
        assert obj.lookup_name == name
        assert obj.lookup_query == query
        assert obj.variable_type == "runway"

    def test___iter__(self) -> None:
        """Test __iter__."""
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        assert list(iter(obj)) == [obj]

    def test___repr__(self) -> None:
        """Test __repr__."""
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        assert repr(obj) == "Lookup[Literal[test] Literal[query]]"
        obj._resolve("resolved")
        assert repr(obj) == "Lookup[resolved (Literal[test] Literal[query])]"

    def test_resolved(self) -> None:
        """Test resolved."""
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        assert obj.resolved is False
        obj._resolved = True
        assert obj.resolved is True

    def test_resolve_exception(self, mocker: MockerFixture) -> None:
        """Test resolve raise Exception."""
        mocker.patch.object(MockLookupHandler, "handle", side_effect=Exception)
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        with pytest.raises(FailedLookup) as excinfo:
            obj.resolve(MagicMock(), MagicMock())
        assert isinstance(excinfo.value.cause, Exception)
        assert excinfo.value.lookup == obj

    def test_resolve(self, mocker: MockerFixture) -> None:
        """Test resolve."""
        kwargs = {
            "context": MagicMock(),
            "provider": MagicMock(),
            "variables": MagicMock(),
            "kwarg": "something",
        }
        mock_handle = mocker.patch.object(MockLookupHandler, "handle", return_value="resolved")
        mock_resolve = mocker.patch.object(VariableValueLookup, "_resolve", return_value=None)
        mock_resolve_query = mocker.patch.object(VariableValueLiteral, "resolve")
        obj = VariableValueLookup(VariableValueLiteral("test"), VariableValueLiteral("query"))
        assert not obj.resolve(**kwargs)  # type: ignore
        mock_resolve_query.assert_called_once_with(**kwargs)
        mock_handle.assert_called_once_with("query", **kwargs)
        mock_resolve.assert_called_once_with("resolved")

    def test_simplified(self) -> None:
        """Test simplified."""
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        assert obj.simplified == obj

    def test___str__(self) -> None:
        """Test __str__."""
        assert str(VariableValueLookup(VariableValueLiteral("test"), "query")) == "${test query}"

    def test_value(self) -> None:
        """Test value."""
        obj = VariableValueLookup(VariableValueLiteral("test"), "query")
        assert obj.resolved is False
        with pytest.raises(UnresolvedVariableValue):
            assert obj.value
        obj._resolve("success")
        assert obj.resolved is True
        assert obj.value == "success"


class TestVariableValuePydanticModel:
    """Test VariableValuePydanticModel."""

    class ModelClass(BaseModel):
        """Model class for testing."""

        test: Any = "val"

    def test___delitem__(self) -> None:
        """Test __delitem__."""
        obj = VariableValuePydanticModel(self.ModelClass())
        assert "test" in obj
        del obj["test"]
        assert "test" not in obj

    def test___getitem__(self, mocker: MockerFixture) -> None:
        """Test __getitem__."""
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value="parsed_val")
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj["test"] == "parsed_val"

    def test___init__(self, mocker: MockerFixture) -> None:
        """Test __init__."""
        mock_parse_obj = mocker.patch.object(
            VariableValuePydanticModel, "parse_obj", return_value="parsed_val"
        )
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj._data == {"test": mock_parse_obj.return_value}
        assert obj._model_class == self.ModelClass
        mock_parse_obj.assert_called_once_with("val", variable_type="cfngin")
        assert obj.variable_type == "cfngin"

    def test___iter__(self) -> None:
        """Test __iter__."""
        obj = VariableValuePydanticModel(self.ModelClass())
        assert list(iter(obj)) == ["test"]

    def test___len__(self) -> None:
        """Test __len__."""
        obj = VariableValuePydanticModel(self.ModelClass())
        assert len(obj) == 1

    def test___repr__(self) -> None:
        """Test __repr__."""
        obj = VariableValuePydanticModel(self.ModelClass())
        assert repr(obj) == "ModelClass[test=Literal[val]]"

    def test___setitem__(self, mocker: MockerFixture) -> None:
        """Test __setitem__."""
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value="parsed_val")
        obj = VariableValuePydanticModel(self.ModelClass())
        obj["test"] = "new"  # type: ignore
        assert obj["test"] == "new"

    def test_dependencies(self, mocker: MockerFixture) -> None:
        """Test dependencies."""
        mock_literal = MagicMock(dependencies=set("foobar"))
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value=mock_literal)
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj.dependencies == mock_literal.dependencies

    def test_resolve(self, cfngin_context: MockCfnginContext, mocker: MockerFixture) -> None:
        """Test resolve."""
        mock_literal = MagicMock()
        mock_provider = MagicMock()
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value=mock_literal)
        obj = VariableValuePydanticModel(self.ModelClass())
        assert not obj.resolve(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},  # type: ignore
            kwarg="test",
        )
        mock_literal.resolve.assert_called_once_with(
            cfngin_context,
            provider=mock_provider,
            variables={"var": "something"},
            kwarg="test",
        )

    @pytest.mark.parametrize("resolved", [False, True])
    def test_resolved(self, mocker: MockerFixture, resolved: bool) -> None:
        """Test resolved."""
        mock_literal = MagicMock(resolved=resolved)
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value=mock_literal)
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj.resolved is resolved

    def test_simplified(self, mocker: MockerFixture) -> None:
        """Test simplified."""
        mock_literal = MagicMock(simplified="simplified")
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value=mock_literal)
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj.simplified == {"test": "simplified"}

    def test_value(self, mocker: MockerFixture) -> None:
        """Test value."""
        mock_literal = MagicMock(value="value")
        mocker.patch.object(VariableValuePydanticModel, "parse_obj", return_value=mock_literal)
        obj = VariableValuePydanticModel(self.ModelClass())
        assert obj.value == self.ModelClass(test=mock_literal.value)
