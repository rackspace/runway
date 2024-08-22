"""Tests for runway.cfngin.lookups.handlers.file."""

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none
from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pydantic import ValidationError
from troposphere import Base64, Join

from runway.cfngin.lookups.handlers.file import CODECS, ArgsDataModel, FileLookup

if TYPE_CHECKING:
    from pathlib import Path


def to_template_dict(obj: Any) -> Any:
    """Extract the CFN template dict of an object for test comparisons."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {key: to_template_dict(value) for (key, value) in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_template_dict(item) for item in obj)
    return obj


def assert_template_dicts(obj1: Any, obj2: Any) -> None:
    """Assert two template dicts are equal."""
    assert to_template_dict(obj1) == to_template_dict(obj2)


class TestArgsDataModel:
    """Test ArgsDataModel."""

    def test__validate_supported_codec_raise_value_error(self) -> None:
        """Test _validate_supported_codec raise ValueError."""
        with pytest.raises(
            ValidationError,
            match=rf".*Value error, Codec 'foo' must be one of: {', '.join(CODECS)}",
        ):
            ArgsDataModel(codec="foo")


class TestFileLookup:
    """Test FileLookup."""

    def test_handle_base64(self, tmp_path: Path) -> None:
        """Test handle base64."""
        data = "foobar"
        expected = base64.b64encode(data.encode("utf-8")).decode("utf-8")
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert FileLookup.handle(f"base64:file://{tmp_file}") == expected
        assert FileLookup.handle(f"base64:{data}") == expected

    def test_handle_json(self, tmp_path: Path) -> None:
        """Test handle json."""
        expected = {"foo": "bar", "foobar": [1, None]}
        data = json.dumps(expected)
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert FileLookup.handle(f"json:file://{tmp_file}") == expected
        assert FileLookup.handle(f"json:{data}") == expected

    def test_handle_json_parameterized(self, tmp_path: Path) -> None:
        """Test handle json-parameterized."""
        expected = {
            "foo": ["bar", Join("", ["", {"Ref": "fooParam"}, ""])],
            "bar": {
                "foobar": Join("", ["", {"Ref": "foobarParam"}, ""]),
                "barfoo": 1,
            },
        }
        data = json.dumps(
            {
                "foo": ["bar", "{{fooParam}}"],
                "bar": {"foobar": "{{foobarParam}}", "barfoo": 1},
            }
        )
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert_template_dicts(FileLookup.handle(f"json-parameterized:file://{tmp_file}"), expected)
        assert_template_dicts(FileLookup.handle(f"json-parameterized:{data}"), expected)

    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                "Test {{Interpolation}} Here",
                Join("", ["Test ", {"Ref": "Interpolation"}, " Here"]),
            ),
            ("Test Without Interpolation Here", "Test Without Interpolation Here"),
        ],
    )
    def test_handle_parameterized(self, data: str, expected: Any, tmp_path: Path) -> None:
        """Test handle parameterized."""
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert_template_dicts(FileLookup.handle(f"parameterized:file://{tmp_file}"), expected)
        assert_template_dicts(FileLookup.handle(f"parameterized:{data}"), expected)

    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                "Test {{Interpolation}} Here",
                Base64(Join("", ["Test ", {"Ref": "Interpolation"}, " Here"])),
            ),
            (
                "Test Without Interpolation Here",
                Base64("Test Without Interpolation Here"),
            ),
        ],
    )
    def test_handle_parameterized_b64(self, data: str, expected: Base64, tmp_path: Path) -> None:
        """Test handle parameterized-b64."""
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert_template_dicts(FileLookup.handle(f"parameterized-b64:file://{tmp_file}"), expected)
        assert_template_dicts(FileLookup.handle(f"parameterized-b64:{data}"), expected)

    def test_handle_plain(self, tmp_path: Path) -> None:
        """Test handle plain."""
        expected = "foobar"
        tmp_file = tmp_path / "test"
        tmp_file.write_text(expected, encoding="utf-8")

        assert FileLookup.handle(f"plain:file://{tmp_file}") == expected
        assert FileLookup.handle(f"plain:{expected}") == expected

    def test_handle_raise_validation_error(self) -> None:
        """Test handle raise ValidationError."""
        with pytest.raises(
            ValidationError,
            match=rf".*Value error, Codec 'foo' must be one of: {', '.join(CODECS)}",
        ):
            FileLookup.handle("foo:bar")

    def test_handle_raise_value_error(self) -> None:
        """Test handle raise ValueError."""
        with pytest.raises(ValueError, match="Query 'foo' doesn't match regex: "):
            FileLookup.handle("foo")

    def test_handle_yaml(self, tmp_path: Path) -> None:
        """Test handle yaml."""
        expected = {"foo": "bar", "foobar": [1, None]}
        data = yaml.dump(expected)
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert FileLookup.handle(f"yaml:file://{tmp_file}") == expected
        assert FileLookup.handle(f"yaml:{data}") == expected

    def test_handle_yaml_parameterized(self, tmp_path: Path) -> None:
        """Test handle yaml-parameterized."""
        expected = {
            "foo": ["bar", Join("", ["", {"Ref": "fooParam"}, ""])],
            "bar": {"foobar": Join("", ["", {"Ref": "foobarParam"}, ""]), "barfoo": 1},
        }
        data = yaml.dump(
            {
                "foo": ["bar", "{{fooParam}}"],
                "bar": {"foobar": "{{foobarParam}}", "barfoo": 1},
            }
        )
        tmp_file = tmp_path / "test"
        tmp_file.write_text(data, encoding="utf-8")

        assert_template_dicts(FileLookup.handle(f"yaml-parameterized:file://{tmp_file}"), expected)
        assert_template_dicts(FileLookup.handle(f"yaml-parameterized:{data}"), expected)
