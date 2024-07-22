"""Tests for lookup handler base class."""

from __future__ import annotations

import json
from typing import Optional
from unittest.mock import MagicMock

import pytest
import yaml

from runway.lookups.handlers.base import LookupHandler
from runway.utils import MutableMap
from runway.variables import VariableValue


class TestLookupHandler:
    """Tests for LookupHandler."""

    def test_abstract_handle(self) -> None:
        """Handle should not be implimented."""
        with pytest.raises(NotImplementedError):
            LookupHandler.handle(None, None)  # type: ignore

    def test_dependencies(self) -> None:
        """Test dependencies.

        This should always return an empty set.

        """
        assert isinstance(LookupHandler.dependencies(MagicMock(autospec=VariableValue)), set)

    def test_format_results(self) -> None:
        """Test format_results."""
        test_dict = {
            "nested": {"bool": True, "nested_key": "nested_value"},
            "test_key": "test_value",
        }
        mute_map = MutableMap(**test_dict.copy())

        assert LookupHandler.format_results(test_dict) == test_dict
        assert LookupHandler.format_results(mute_map) == test_dict

        assert LookupHandler.format_results(test_dict, get="test_key") == test_dict["test_key"]
        assert LookupHandler.format_results(mute_map, get="test_key") == mute_map["test_key"]
        assert LookupHandler.format_results(mute_map, get="nested") == mute_map["nested"].data
        assert (
            LookupHandler.format_results(mute_map, get="nested.nested_key")
            == mute_map["nested"]["nested_key"]
        )
        assert LookupHandler.format_results(mute_map, get="nested.bool")

        assert LookupHandler.format_results(mute_map, transform="str") == json.dumps(
            json.dumps(test_dict, indent=0)
        )
        assert LookupHandler.format_results(mute_map, transform="str", indent=2) == json.dumps(
            json.dumps(test_dict, indent=2)
        )
        assert (
            LookupHandler.format_results(mute_map, get="nested.bool", transform="str") == '"True"'
        )

        with pytest.raises(TypeError):
            LookupHandler.format_results(["something"], get="key")

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("", ""),
            ("None", None),
            ("NoneType", "NoneType"),
            ("Null", None),
            ("none", None),
            ("null", None),
            ("undefined", "undefined"),
        ],
    )
    def test_format_results_handle_none(self, value: str, expected: Optional[str]) -> None:
        """Test format_results."""
        assert LookupHandler.format_results(value) == expected
        if isinstance(expected, str):
            assert LookupHandler.format_results(value, transform="str") == expected
        else:  # value should be returned "as is"
            assert LookupHandler.format_results(value, transform="str") == value

    def test_load_no_parser(self) -> None:
        """Test load with no parser."""
        assert LookupHandler.load("something") == "something"

    def test_load_list(self) -> None:
        """Test load parsers with a list result."""
        value = ["something", "something-else"]
        assert LookupHandler.load(json.dumps(value), parser="json") == value
        assert LookupHandler.load(yaml.dump(value), parser="yaml") == value

    @pytest.mark.parametrize(
        "query, raw_args, expected_args",
        [
            ("query", None, {}),
            ("query", "key1=val1", {"key1": "val1"}),
            (
                "query.something",
                "key1=val1,key2=val2",
                {"key1": "val1", "key2": "val2"},
            ),
            (
                "query.something",
                "key1=val1, key2=val2",
                {"key1": "val1", "key2": "val2"},
            ),
            ("query-something", "key1=val-1", {"key1": "val-1"}),
            ("query:something", "key1=val:1", {"key1": "val:1"}),
            ("query=something", "key1=val=1", {"key1": "val=1"}),
            ("query==something", "key1=val==1", {"key1": "val==1"}),
        ],
    )
    def test_parse(
        self,
        query: str,
        raw_args: Optional[dict[str, str]],
        expected_args: dict[str, str],
    ) -> None:
        """Test parse."""
        value = f"{query}::{raw_args}"
        result_query, result_args = LookupHandler.parse(value if raw_args else query)
        assert result_query == query
        assert result_args == expected_args

    def test_transform_bool_to_bool(self) -> None:
        """Bool should be returned as is."""
        result_true = LookupHandler.transform(True, to_type="bool")
        result_false = LookupHandler.transform(False, to_type="bool")

        assert isinstance(result_true, bool)
        assert isinstance(result_false, bool)
        assert result_true
        assert not result_false

    def test_transform_no_type(self) -> None:
        """Test transform with no type."""
        assert isinstance(LookupHandler.transform(True, to_type=None), bool)
        assert isinstance(LookupHandler.transform(["something"], to_type=None), list)
        assert isinstance(LookupHandler.transform("something", to_type=None), str)

    def test_transform_str_to_bool(self) -> None:
        """String should be transformed using str2bool."""
        result_true = LookupHandler.transform("true", to_type="bool")
        result_false = LookupHandler.transform("false", to_type="bool")

        assert isinstance(result_true, bool)
        assert isinstance(result_false, bool)
        assert result_true
        assert not result_false

    def test_transform_type_check(self) -> None:
        """Transform to bool type check."""
        with pytest.raises(TypeError):
            LookupHandler.transform({"key1": "val1"}, to_type="bool")

        with pytest.raises(TypeError):
            LookupHandler.transform(["li1"], to_type="bool")

        with pytest.raises(TypeError):
            LookupHandler.transform(10, to_type="bool")

        with pytest.raises(TypeError):
            LookupHandler.transform(10.0, to_type="bool")

        with pytest.raises(TypeError):
            LookupHandler.transform(None, to_type="bool")

    def test_transform_str_direct(self) -> None:
        """Test types that are directly transformed to strings."""
        assert LookupHandler.transform("test", to_type="str") == "test"
        assert LookupHandler.transform({"key1": "val1"}, to_type="str") == json.dumps(
            json.dumps({"key1": "val1"}, indent=0)
        )
        assert LookupHandler.transform(True, to_type="str") == '"True"'

    def test_transform_str_list(self) -> None:
        """Test list type joined to create string."""
        assert LookupHandler.transform(["val1", "val2"], to_type="str") == "val1,val2"
        assert LookupHandler.transform({"val"}, to_type="str") == "val"
        assert LookupHandler.transform(("val1", "val2"), to_type="str") == "val1,val2"

    def test_transform_str_list_delimiter(self) -> None:
        """Test list to string with a specified delimiter."""
        assert (
            LookupHandler.transform(["val1", "val2"], to_type="str", delimiter="|") == "val1|val2"
        )
