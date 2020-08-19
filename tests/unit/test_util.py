"""Test Runway utils."""
# pylint: disable=no-self-use
import datetime
import json
import logging
import os
import string
import sys
from decimal import Decimal

import pytest
from mock import MagicMock, patch

from runway.util import (
    JsonEncoder,
    MutableMap,
    SafeHaven,
    argv,
    environ,
    load_object_from_string,
)

MODULE = "runway.util"
VALUE = {
    "bool_val": False,
    "dict_val": {"test": "success"},
    "list_val": ["success"],
    "nested_val": {"dict_val": {"test": "success"}},
    "str_val": "test",
}


class TestJsonEncoder(object):
    """Test runway.util.JsonEncoder."""

    @pytest.mark.parametrize(
        "provided, expected", [(datetime.datetime.now(), str), (Decimal("1.1"), float)]
    )
    def test_supported_types(self, provided, expected):
        """Test encoding of supported data types."""
        assert isinstance(JsonEncoder().default(provided), expected)

    @pytest.mark.parametrize("provided", [(None)])
    def test_unsupported_types(self, provided):
        """Test encoding of unsupported data types."""
        with pytest.raises(TypeError):
            assert not JsonEncoder().default(provided)


class TestMutableMap:
    """Test for the custom MutableMap data type."""

    def test_bool(self):
        """Validates the bool value.

        Also tests setting an attr using bracket notation.

        """
        mute_map = MutableMap()

        assert not mute_map

        mute_map["str_val"] = "test"

        assert mute_map

    def test_data(self):
        """Validate the init process and retrieving sanitized data."""
        mute_map = MutableMap(**VALUE)

        assert mute_map.data == VALUE

    def test_delete(self):
        """Validate that keys can be deleted.

        Uses dot and bracket notation.

        Also tests `get` method.

        """
        mute_map = MutableMap(**VALUE)
        del mute_map.str_val
        del mute_map["dict_val"]

        assert not mute_map.get("str_val")
        assert not mute_map.get("dict_val")

    def test_find(self):
        """Validate the `find` method with and without `ignore_cache`.

        Also tests the `clear_found_cache` method and setting an attr value
        using dot notation.

        """
        mute_map = MutableMap(**VALUE)

        assert mute_map.find("str_val") == VALUE["str_val"]

        mute_map.str_val = "new_val"

        assert mute_map.find("str_val") == VALUE["str_val"]
        assert mute_map.find("str_val", ignore_cache=True) == "new_val"

        mute_map.clear_found_cache()

        assert mute_map.find("str_val") == "new_val"

    def test_find_default(self):
        """Validate default value functionality."""
        mute_map = MutableMap(**VALUE)

        assert (
            mute_map.find("NOT_VALID", "default_val") == "default_val"
        ), "default should be used"
        assert (
            mute_map.find("str_val", "default_val") == VALUE["str_val"]
        ), "default should be ignored"


class TestSafeHaven(object):
    """Test SafeHaven context manager."""

    TEST_PARAMS = [
        (None),
        ("string"),
        ({}),
        ({"TEST_KEY": "TEST_VAL"}),
        (["runway", "test"]),
    ]

    def test_context_manager_magic(self, caplog, monkeypatch):
        """Test init and the attributes it sets."""
        mock_reset_all = MagicMock()
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(MODULE + ".os", MagicMock())
        monkeypatch.setattr(MODULE + ".sys", MagicMock())
        monkeypatch.setattr(SafeHaven, "reset_all", mock_reset_all)

        with SafeHaven() as result:
            assert isinstance(result, SafeHaven)
        mock_reset_all.assert_called_once()
        assert caplog.messages == [
            "entering a safe haven...",
            "leaving the safe haven...",
        ]

    @pytest.mark.parametrize("provided", TEST_PARAMS)
    def test_os_environ(self, provided, caplog, monkeypatch):
        """Test os.environ interactions."""
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(SafeHaven, "reset_all", MagicMock())

        orig_val = dict(os.environ)
        expected_val = dict(os.environ)
        expected_logs = [
            "entering a safe haven...",
            "resetting os.environ: %s" % json.dumps(orig_val),
            "leaving the safe haven...",
        ]

        if isinstance(provided, dict):
            expected_val.update(provided)

        with SafeHaven(environ=provided) as obj:
            assert os.environ == expected_val
            os.environ.update({"SOMETHING_ELSE": "val"})
            obj.reset_os_environ()
        assert os.environ == orig_val
        assert caplog.messages == expected_logs

    def test_reset_all(self, caplog, monkeypatch):
        """Test reset_all."""
        mock_method = MagicMock()
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(SafeHaven, "reset_os_environ", mock_method)
        monkeypatch.setattr(SafeHaven, "reset_sys_argv", mock_method)
        monkeypatch.setattr(SafeHaven, "reset_sys_modules", mock_method)
        monkeypatch.setattr(SafeHaven, "reset_sys_path", mock_method)

        expected_logs = [
            "entering a safe haven...",
            "resetting all managed values...",
            "leaving the safe haven...",
            "resetting all managed values...",
        ]

        with SafeHaven() as obj:
            obj.reset_all()
            assert mock_method.call_count == 4
        assert mock_method.call_count == 8  # called again on exit
        assert caplog.messages == expected_logs

    @pytest.mark.parametrize("provided", TEST_PARAMS)
    def test_sys_argv(self, provided, caplog, monkeypatch):
        """Test sys.argv interactions."""
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(SafeHaven, "reset_all", MagicMock())

        orig_val = list(sys.argv)
        expected_val = provided if isinstance(provided, list) else list(sys.argv)
        expected_logs = [
            "entering a safe haven...",
            "resetting sys.argv: %s" % json.dumps(orig_val),
            "leaving the safe haven...",
        ]

        with SafeHaven(argv=provided) as obj:
            assert sys.argv == expected_val
            sys.argv.append("something-else")
            obj.reset_sys_argv()
        assert sys.argv == orig_val
        assert caplog.messages == expected_logs

    def test_sys_modules(self, caplog, monkeypatch):
        """Test sys.modules interactions."""
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(SafeHaven, "reset_all", MagicMock())

        # pylint: disable=unnecessary-comprehension
        orig_val = {k: v for k, v in sys.modules.items()}
        expected_logs = ["entering a safe haven...", "resetting sys.modules..."]

        with SafeHaven() as obj:
            from .fixtures import mock_hooks  # noqa pylint: disable=E,W,C

            assert sys.modules != orig_val
            obj.reset_sys_modules()
        assert sys.modules == orig_val
        assert caplog.messages[:2] == expected_logs
        assert caplog.messages[-1] == "leaving the safe haven..."

    def test_sys_modules_exclude(self, monkeypatch):
        """Test sys.modules interations with excluded module."""
        monkeypatch.setattr(SafeHaven, "reset_all", MagicMock())

        module = "tests.unit.fixtures.mock_hooks"

        assert module not in sys.modules
        with SafeHaven(sys_modules_exclude=module) as obj:
            from .fixtures import mock_hooks  # noqa pylint: disable=E,W,C

            assert module in sys.modules
            obj.reset_sys_modules()
        assert module in sys.modules
        # cleanup
        del sys.modules[module]
        assert module not in sys.modules

    @pytest.mark.parametrize("provided", TEST_PARAMS)
    def test_sys_path(self, provided, caplog, monkeypatch):
        """Test sys.path interactions."""
        caplog.set_level(logging.DEBUG, "runway.SafeHaven")
        monkeypatch.setattr(SafeHaven, "reset_all", MagicMock())

        orig_val = list(sys.path)
        expected_val = provided if isinstance(provided, list) else list(sys.path)
        expected_logs = [
            "entering a safe haven...",
            "resetting sys.path: %s" % json.dumps(orig_val),
            "leaving the safe haven...",
        ]

        with SafeHaven(sys_path=provided) as obj:
            assert sys.path == expected_val
            sys.path.append("something-else")
            obj.reset_sys_path()
        assert sys.path == orig_val
        assert caplog.messages == expected_logs


@patch.object(sys, "argv", ["runway", "deploy"])
def test_argv():
    """Test argv."""
    orig_expected = ["runway", "deploy"]
    override = ["stacker", "build", "test.yml"]

    assert sys.argv == orig_expected, "validate original value"

    with argv(*override):
        assert sys.argv == override, "validate override"

    assert sys.argv == orig_expected, "validate value returned to original"


def test_environ():
    """Test environ."""
    orig_expected = dict(os.environ)
    override = {"TEST_PARAM": "override", "new_param": "value"}
    override_expected = dict(orig_expected)
    override_expected.update(override)

    assert os.environ == orig_expected, "validate original value"

    with environ(override):
        assert os.environ == override_expected, "validate override"
        assert os.environ.pop("new_param") == "value"

    assert os.environ == orig_expected, "validate value returned to original"


def test_load_object_from_string():
    """Test load object from string."""
    tests = (
        ("string.Template", string.Template),
        ("os.path.basename", os.path.basename),
        ("string.ascii_letters", string.ascii_letters),
    )
    for test in tests:
        assert load_object_from_string(test[0]) is test[1]

    obj_path = "tests.unit.fixtures.mock_hooks.GLOBAL_VALUE"
    # check value from os.environ
    assert load_object_from_string(obj_path, try_reload=True) == "us-east-1"

    with environ({"AWS_DEFAULT_REGION": "us-west-2"}):
        # check value from os.environ after changing it to ensure reload
        assert load_object_from_string(obj_path, try_reload=True) == "us-west-2"


@patch("runway.util.six")
def test_load_object_from_string_reload_conditions(mock_six):
    """Test load_object_from_string reload conditions."""
    mock_six.moves.reload_module.return_value = MagicMock()
    builtin_test = "sys.version_info"
    mock_hook = "tests.unit.fixtures.mock_hooks.GLOBAL_VALUE"

    try:
        del sys.modules["tests.unit.fixtures.mock_hooks"]
    except:  # noqa pylint: disable=bare-except
        pass

    load_object_from_string(builtin_test, try_reload=False)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(builtin_test, try_reload=True)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(mock_hook, try_reload=True)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(mock_hook, try_reload=True)
    mock_six.moves.reload_module.assert_called_once()
