"""Tests for runway.cfngin.lookups.handlers.file."""
# pylint: disable=no-self-use
# pyright: basic, reportUnknownArgumentType=none, reportUnknownVariableType=none
import base64
import json
import unittest
from typing import Any

import mock
import yaml
from troposphere import Base64, GenericHelperFn, Join

from runway.cfngin.lookups.handlers.file import (
    FileLookup,
    json_codec,
    parameterized_codec,
    yaml_codec,
)


def to_template_dict(obj: Any) -> Any:
    """Extract the CFN template dict of an object for test comparisons."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {key: to_template_dict(value) for (key, value) in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_template_dict(item) for item in obj)
    return obj


class TestFileTranslator(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.file.FileLookup."""

    @staticmethod
    def assertTemplateEqual(  # noqa: N802 pylint: disable=invalid-name
        left: Any, right: Any
    ) -> None:
        """Assert that two codec results are equivalent.

        Convert both sides to their template representations, since Troposphere
        objects are not natively comparable.

        """
        return to_template_dict(left) == to_template_dict(right)

    def test_parameterized_codec_b64(self) -> None:
        """Test parameterized codec b64."""
        expected = Base64(Join("", ["Test ", {"Ref": "Interpolation"}, " Here"]))
        out = parameterized_codec("Test {{Interpolation}} Here", True)
        self.assertEqual(Base64, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_parameterized_codec_plain(self) -> None:
        """Test parameterized codec plain."""
        expected = Join("", ["Test ", {"Ref": "Interpolation"}, " Here"])
        out = parameterized_codec("Test {{Interpolation}} Here", False)
        self.assertEqual(GenericHelperFn, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_parameterized_codec_plain_no_interpolation(self) -> None:
        """Test parameterized codec plain no interpolation."""
        expected = "Test Without Interpolation Here"
        out = parameterized_codec("Test Without Interpolation Here", False)
        self.assertEqual(GenericHelperFn, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_yaml_codec_raw(self) -> None:
        """Test yaml codec raw."""
        structured = {"Test": [1, None, "unicode ✓", {"some": "obj"}]}
        # Note: must use safe_dump, since regular dump adds !python/unicode
        # tags, which we don't want, or we can't be sure we're correctly
        # loading string as unicode.
        raw = yaml.safe_dump(structured)

        out = yaml_codec(raw, parameterized=False)
        self.assertEqual(structured, out)

    def test_yaml_codec_parameterized(self) -> None:
        """Test yaml codec parameterized."""
        processed = {"Test": Join("", ["Test ", {"Ref": "Interpolation"}, " Here"])}
        structured = {"Test": "Test {{Interpolation}} Here"}
        raw = yaml.safe_dump(structured)

        out = yaml_codec(raw, parameterized=True)
        self.assertTemplateEqual(processed, out)

    def test_json_codec_raw(self) -> None:
        """Test json codec raw."""
        structured = {"Test": [1, None, "str", {"some": "obj"}]}
        raw = json.dumps(structured)

        out = json_codec(raw, parameterized=False)
        self.assertEqual(structured, out)

    def test_json_codec_parameterized(self) -> None:
        """Test json codec parameterized."""
        processed = {"Test": Join("", ["Test ", {"Ref": "Interpolation"}, " Here"])}
        structured = {"Test": "Test {{Interpolation}} Here"}
        raw = json.dumps(structured)

        out = json_codec(raw, parameterized=True)
        self.assertTemplateEqual(processed, out)

    @mock.patch(
        "runway.cfngin.lookups.handlers.file.read_value_from_path", return_value=""
    )
    def test_file_loaded(self, content_mock: mock.MagicMock) -> None:
        """Test file loaded."""
        FileLookup.handle("plain:file://tmp/test")
        content_mock.assert_called_with("file://tmp/test")

    @mock.patch(
        "runway.cfngin.lookups.handlers.file.read_value_from_path",
        return_value="Hello, world",
    )
    def test_handler_plain(self, _: mock.MagicMock) -> None:
        """Test handler plain."""
        out = FileLookup.handle("plain:file://tmp/test")
        self.assertEqual("Hello, world", out)

    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_b64(self, content_mock: mock.MagicMock) -> None:
        """Test handler b64."""
        plain = "Hello, world"
        encoded = base64.b64encode(plain.encode("utf8")).decode("utf-8")

        content_mock.return_value = plain
        out = FileLookup.handle("base64:file://tmp/test")
        self.assertEqual(encoded, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.parameterized_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_parameterized(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("parameterized:file://tmp/test")
        codec_mock.assert_called_once_with(content_mock.return_value, False)

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.parameterized_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_parameterized_b64(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler parameterized b64."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("parameterized-b64:file://tmp/test")
        codec_mock.assert_called_once_with(content_mock.return_value, True)

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.yaml_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_yaml(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler yaml."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("yaml:file://tmp/test")
        codec_mock.assert_called_once_with(
            content_mock.return_value, parameterized=False
        )

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.yaml_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_yaml_parameterized(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler yaml parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("yaml-parameterized:file://tmp/test")
        codec_mock.assert_called_once_with(
            content_mock.return_value, parameterized=True
        )

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.json_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_json(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler json."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("json:file://tmp/test")
        codec_mock.assert_called_once_with(
            content_mock.return_value, parameterized=False
        )

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.json_codec")
    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_handler_json_parameterized(
        self, content_mock: mock.MagicMock, codec_mock: mock.MagicMock
    ) -> None:
        """Test handler json parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle("json-parameterized:file://tmp/test")
        codec_mock.assert_called_once_with(
            content_mock.return_value, parameterized=True
        )

        self.assertEqual(result, out)

    @mock.patch("runway.cfngin.lookups.handlers.file.read_value_from_path")
    def test_unknown_codec(self, _: mock.MagicMock) -> None:
        """Test unknown codec."""
        with self.assertRaises(KeyError):
            FileLookup.handle("bad:file://tmp/test")
