# encoding: utf-8
"""Tests for runway.cfngin.lookups.handlers.file.

.. note: ``encoding: utf-8`` is required for python2 support due to a character
         in a string in ``test_yaml_codec_raw``.

"""
import base64
import json
import unittest

import mock
import yaml
from troposphere import Base64, GenericHelperFn, Join

from runway.cfngin.lookups.handlers.file import (FileLookup, json_codec,
                                                 parameterized_codec,
                                                 yaml_codec)


def to_template_dict(obj):
    """Extract the CFN template dict of an object for test comparisons."""
    if hasattr(obj, 'to_dict') and callable(obj.to_dict):
        return obj.to_dict()
    elif isinstance(obj, dict):
        return dict((key, to_template_dict(value))
                    for (key, value) in obj.items())
    elif isinstance(obj, (list, tuple)):
        return type(obj)(to_template_dict(item) for item in obj)
    else:
        return obj


class TestFileTranslator(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.file.FileLookup."""

    @staticmethod
    def assertTemplateEqual(left, right):  # noqa: N802 pylint: disable=invalid-name
        """Assert that two codec results are equivalent.

        Convert both sides to their template representations, since Troposphere
        objects are not natively comparable.

        """
        return to_template_dict(left) == to_template_dict(right)

    def test_parameterized_codec_b64(self):
        """Test parameterized codec b64."""
        expected = Base64(
            Join(u'', [u'Test ', {u'Ref': u'Interpolation'}, u' Here'])
        )

        out = parameterized_codec(u'Test {{Interpolation}} Here', True)
        self.assertEqual(Base64, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_parameterized_codec_plain(self):
        """Test parameterized codec plain."""
        expected = Join(u'', [u'Test ', {u'Ref': u'Interpolation'}, u' Here'])

        out = parameterized_codec(u'Test {{Interpolation}} Here', False)
        self.assertEqual(GenericHelperFn, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_parameterized_codec_plain_no_interpolation(self):
        """Test parameterized codec plain no interpolation."""
        expected = u'Test Without Interpolation Here'

        out = parameterized_codec(u'Test Without Interpolation Here', False)
        self.assertEqual(GenericHelperFn, out.__class__)
        self.assertTemplateEqual(expected, out)

    def test_yaml_codec_raw(self):
        """Test yaml codec raw."""
        structured = {
            u'Test': [1, None, u'unicode ✓', {u'some': u'obj'}]
        }
        # Note: must use safe_dump, since regular dump adds !python/unicode
        # tags, which we don't want, or we can't be sure we're correctly
        # loading string as unicode.
        raw = yaml.safe_dump(structured)

        out = yaml_codec(raw, parameterized=False)
        self.assertEqual(structured, out)

    def test_yaml_codec_parameterized(self):
        """Test yaml codec parameterized."""
        processed = {
            u'Test': Join(u'', [u'Test ', {u'Ref': u'Interpolation'},
                                u' Here'])
        }
        structured = {
            u'Test': u'Test {{Interpolation}} Here'
        }
        raw = yaml.safe_dump(structured)

        out = yaml_codec(raw, parameterized=True)
        self.assertTemplateEqual(processed, out)

    def test_json_codec_raw(self):
        """Test json codec raw."""
        structured = {
            u'Test': [1, None, u'str', {u'some': u'obj'}]
        }
        raw = json.dumps(structured)

        out = json_codec(raw, parameterized=False)
        self.assertEqual(structured, out)

    def test_json_codec_parameterized(self):
        """Test json codec parameterized."""
        processed = {
            u'Test': Join(u'', [u'Test ', {u'Ref': u'Interpolation'},
                                u' Here'])
        }
        structured = {
            u'Test': u'Test {{Interpolation}} Here'
        }
        raw = json.dumps(structured)

        out = json_codec(raw, parameterized=True)
        self.assertTemplateEqual(processed, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path',
                return_value='')
    def test_file_loaded(self, content_mock):
        """Test file loaded."""
        FileLookup.handle(u'plain:file://tmp/test')
        content_mock.assert_called_with(u'file://tmp/test')

    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path',
                return_value=u'Hello, world')
    def test_handler_plain(self, _):
        """Test handler plain."""
        out = FileLookup.handle(u'plain:file://tmp/test')
        self.assertEqual(u'Hello, world', out)

    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_b64(self, content_mock):
        """Test handler b64."""
        plain = u'Hello, world'
        encoded = base64.b64encode(plain.encode('utf8')).decode('utf-8')

        content_mock.return_value = plain
        out = FileLookup.handle(u'base64:file://tmp/test')
        self.assertEqual(encoded, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.parameterized_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_parameterized(self, content_mock, codec_mock):
        """Test handler parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'parameterized:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value, False)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.parameterized_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_parameterized_b64(self, content_mock, codec_mock):
        """Test handler parameterized b64."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'parameterized-b64:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value, True)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.yaml_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_yaml(self, content_mock, codec_mock):
        """Test handler yaml."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'yaml:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value,
                                           parameterized=False)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.yaml_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_yaml_parameterized(self, content_mock, codec_mock):
        """Test handler yaml parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'yaml-parameterized:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value,
                                           parameterized=True)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.json_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_json(self, content_mock, codec_mock):
        """Test handler json."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'json:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value,
                                           parameterized=False)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.json_codec')
    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_handler_json_parameterized(self, content_mock, codec_mock):
        """Test handler json parameterized."""
        result = mock.Mock()
        codec_mock.return_value = result

        out = FileLookup.handle(u'json-parameterized:file://tmp/test')
        codec_mock.assert_called_once_with(content_mock.return_value,
                                           parameterized=True)

        self.assertEqual(result, out)

    @mock.patch('runway.cfngin.lookups.handlers.file.read_value_from_path')
    def test_unknown_codec(self, _):
        """Test unknown codec."""
        with self.assertRaises(KeyError):
            FileLookup.handle(u'bad:file://tmp/test')
