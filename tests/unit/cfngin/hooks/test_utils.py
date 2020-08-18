"""Tests for runway.cfngin.hooks.utils."""
# pylint: disable=no-self-use,unused-argument
import queue
import unittest

from mock import call, patch

from runway.cfngin.config import Hook
from runway.cfngin.hooks.utils import handle_hooks

from ..factories import mock_context, mock_provider

HOOK_QUEUE = queue.Queue()


class TestHooks(unittest.TestCase):
    """Tests for runway.cfngin.hooks.utils."""

    def setUp(self):
        """Run before tests."""
        self.context = mock_context(namespace="namespace")
        self.provider = mock_provider(region="us-east-1")

    def test_empty_hook_stage(self):
        """Test empty hook stage."""
        hooks = []
        handle_hooks("fake", hooks, self.provider, self.context)
        self.assertTrue(HOOK_QUEUE.empty())

    def test_missing_required_hook(self):
        """Test missing required hook."""
        hooks = [Hook({"path": "not.a.real.path", "required": True})]
        with self.assertRaises(ImportError):
            handle_hooks("missing", hooks, self.provider, self.context)

    def test_missing_required_hook_method(self):
        """Test missing required hook method."""
        with self.assertRaises(AttributeError):
            hooks = [{"path": "runway.cfngin.hooks.blah", "required": True}]
            handle_hooks("missing", hooks, self.provider, self.context)

    def test_missing_non_required_hook_method(self):
        """Test missing non required hook method."""
        hooks = [Hook({"path": "runway.cfngin.hooks.blah", "required": False})]
        handle_hooks("missing", hooks, self.provider, self.context)
        self.assertTrue(HOOK_QUEUE.empty())

    def test_default_required_hook(self):
        """Test default required hook."""
        hooks = [Hook({"path": "runway.cfngin.hooks.blah"})]
        with self.assertRaises(AttributeError):
            handle_hooks("missing", hooks, self.provider, self.context)

    @patch("runway.cfngin.hooks.utils.load_object_from_string")
    def test_valid_hook(self, mock_load):
        """Test valid hook."""
        mock_load.side_effect = [mock_hook, MockHook]
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.mock_hook",
                    "required": True,
                }
            ),
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.MockHook",
                    "required": True,
                }
            ),
        ]
        handle_hooks("pre_build", hooks, self.provider, self.context)
        assert mock_load.call_count == 2
        mock_load.assert_has_calls(
            [call(hooks[0].path, try_reload=True), call(hooks[1].path, try_reload=True)]
        )
        good = HOOK_QUEUE.get_nowait()
        self.assertEqual(good["provider"].region, "us-east-1")
        with self.assertRaises(queue.Empty):
            HOOK_QUEUE.get_nowait()

    def test_valid_enabled_hook(self):
        """Test valid enabled hook."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.mock_hook",
                    "required": True,
                    "enabled": True,
                }
            )
        ]
        handle_hooks("missing", hooks, self.provider, self.context)
        good = HOOK_QUEUE.get_nowait()
        self.assertEqual(good["provider"].region, "us-east-1")
        with self.assertRaises(queue.Empty):
            HOOK_QUEUE.get_nowait()

    def test_valid_enabled_false_hook(self):
        """Test valid enabled false hook."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.mock_hook",
                    "required": True,
                    "enabled": False,
                }
            )
        ]
        handle_hooks("missing", hooks, self.provider, self.context)
        self.assertTrue(HOOK_QUEUE.empty())

    def test_context_provided_to_hook(self):
        """Test context provided to hook."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.context_hook",
                    "required": True,
                }
            )
        ]
        handle_hooks("missing", hooks, "us-east-1", self.context)

    def test_hook_failure(self):
        """Test hook failure."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.fail_hook",
                    "required": True,
                }
            )
        ]
        with self.assertRaises(SystemExit):
            handle_hooks("fail", hooks, self.provider, self.context)
        hooks = [
            {
                "path": "tests.unit.cfngin.hooks.test_utils.exception_hook",
                "required": True,
            }
        ]
        with self.assertRaises(Exception):
            handle_hooks("fail", hooks, self.provider, self.context)
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.exception_hook",
                    "required": False,
                }
            )
        ]
        # Should pass
        handle_hooks("ignore_exception", hooks, self.provider, self.context)

    def test_return_data_hook(self):
        """Test return data hook."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.result_hook",
                    "data_key": "my_hook_results",
                }
            ),
            # Shouldn't return data
            Hook({"path": "tests.unit.cfngin.hooks.test_utils.context_hook"}),
        ]
        handle_hooks("result", hooks, "us-east-1", self.context)

        self.assertEqual(self.context.hook_data["my_hook_results"]["foo"], "bar")
        # Verify only the first hook resulted in stored data
        self.assertEqual(list(self.context.hook_data.keys()), ["my_hook_results"])

    def test_return_data_hook_duplicate_key(self):
        """Test return data hook duplicate key."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.result_hook",
                    "data_key": "my_hook_results",
                }
            ),
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.result_hook",
                    "data_key": "my_hook_results",
                }
            ),
        ]

        with self.assertRaises(KeyError):
            handle_hooks("result", hooks, "us-east-1", self.context)

    def test_resolve_lookups_in_args(self):
        """Test the resolution of lookups in hook args."""
        hooks = [
            Hook(
                {
                    "path": "tests.unit.cfngin.hooks.test_utils.kwargs_hook",
                    "data_key": "my_hook_results",
                    "args": {"default_lookup": "${default env_var::default_value}"},
                }
            )
        ]
        handle_hooks("lookups", hooks, "us-east-1", self.context)

        self.assertEqual(
            self.context.hook_data["my_hook_results"]["default_lookup"], "default_value"
        )


class MockHook(object):
    """Mock hook class."""

    def __init__(self, **kwargs):
        """Instantiate class."""

    def post_deploy(self):
        """Run during the **post_deploy** stage."""
        return {"status": "success"}

    def post_destroy(self):
        """Run during the **post_destroy** stage."""
        return {"status": "success"}

    def pre_deploy(self):
        """Run during the **pre_deploy** stage."""
        return {"status": "success"}

    def pre_destroy(self):
        """Run during the **pre_destroy** stage."""
        return {"status": "success"}


def mock_hook(*args, **kwargs):
    """Mock hook."""
    HOOK_QUEUE.put(kwargs)
    return True


def fail_hook(*args, **kwargs):
    """Fail hook."""
    return None


def exception_hook(*args, **kwargs):
    """Exception hook."""
    raise Exception


def context_hook(*args, **kwargs):
    """Context hook."""
    return "context" in kwargs


def result_hook(*args, **kwargs):
    """Results hook."""
    return {"foo": "bar"}


def kwargs_hook(*args, **kwargs):
    """Kwargs hook."""
    return kwargs
