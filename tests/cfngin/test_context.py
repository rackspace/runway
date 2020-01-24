"""Tests for runway.cfngin.context."""
import unittest

from runway.cfngin.config import Config, load
from runway.cfngin.context import Context, get_fqn
from runway.cfngin.util import handle_hooks


class TestContext(unittest.TestCase):
    """Tests for runway.cfngin.context.Context."""

    def setUp(self):
        """Run before tests."""
        self.config = Config({
            "namespace": "namespace",
            "stacks": [
                {"name": "stack1"}, {"name": "stack2"}]})

    def test_context_optional_keys_set(self):
        """Test context optional keys set."""
        context = Context(
            config=Config({}),
            stack_names=["stack"],
        )
        self.assertEqual(context.mappings, {})
        self.assertEqual(context.stack_names, ["stack"])

    def test_context_get_stacks(self):
        """Test context get stacks."""
        context = Context(config=self.config)
        self.assertEqual(len(context.get_stacks()), 2)

    def test_context_get_stacks_dict_use_fqn(self):
        """Test context get stacks dict use fqn."""
        context = Context(config=self.config)
        stacks_dict = context.get_stacks_dict()
        stack_names = sorted(stacks_dict.keys())
        self.assertEqual(stack_names[0], "namespace-stack1")
        self.assertEqual(stack_names[1], "namespace-stack2")

    def test_context_get_fqn(self):
        """Test context get fqn."""
        context = Context(config=self.config)
        fqn = context.get_fqn()
        self.assertEqual(fqn, "namespace")

    def test_context_get_fqn_replace_dot(self):
        """Test context get fqn replace dot."""
        context = Context(config=Config({"namespace": "my.namespace"}))
        fqn = context.get_fqn()
        self.assertEqual(fqn, "my-namespace")

    def test_context_get_fqn_empty_namespace(self):
        """Test context get fqn empty namespace."""
        context = Context(config=Config({"namespace": ""}))
        fqn = context.get_fqn("vpc")
        self.assertEqual(fqn, "vpc")
        self.assertEqual(context.tags, {})

    def test_context_namespace(self):
        """Test context namespace."""
        context = Context(config=Config({"namespace": "namespace"}))
        self.assertEqual(context.namespace, "namespace")

    def test_context_get_fqn_stack_name(self):
        """Test context get fqn stack name."""
        context = Context(config=self.config)
        fqn = context.get_fqn("stack1")
        self.assertEqual(fqn, "namespace-stack1")

    def test_context_default_bucket_name(self):
        """Test context default bucket name."""
        context = Context(config=Config({"namespace": "test"}))
        self.assertEqual(context.bucket_name, "stacker-test")

    def test_context_bucket_name_is_overridden_but_is_none(self):
        """Test context bucket name is overridden but is none."""
        config = Config({"namespace": "test", "stacker_bucket": ""})
        context = Context(config=config)
        self.assertEqual(context.bucket_name, None)

        config = Config({"namespace": "test", "stacker_bucket": None})
        context = Context(config=config)
        self.assertEqual(context.bucket_name, "stacker-test")

    def test_context_bucket_name_is_overridden(self):
        """Test context bucket name is overridden."""
        config = Config({"namespace": "test", "stacker_bucket": "bucket123"})
        context = Context(config=config)
        self.assertEqual(context.bucket_name, "bucket123")

    def test_context_default_bucket_no_namespace(self):
        """Test context default bucket no namespace."""
        context = Context(config=Config({"namespace": ""}))
        self.assertEqual(context.bucket_name, None)

        context = Context(config=Config({"namespace": None}))
        self.assertEqual(context.bucket_name, None)

        context = Context(
            config=Config({"namespace": None, "stacker_bucket": ""}))
        self.assertEqual(context.bucket_name, None)

    def test_context_namespace_delimiter_is_overridden_and_not_none(self):
        """Test context namespace delimiter is overridden and not none."""
        config = Config({"namespace": "namespace", "namespace_delimiter": "_"})
        context = Context(config=config)
        fqn = context.get_fqn("stack1")
        self.assertEqual(fqn, "namespace_stack1")

    def test_context_namespace_delimiter_is_overridden_and_is_empty(self):
        """Test context namespace delimiter is overridden and is empty."""
        config = Config({"namespace": "namespace", "namespace_delimiter": ""})
        context = Context(config=config)
        fqn = context.get_fqn("stack1")
        self.assertEqual(fqn, "namespacestack1")

    def test_context_tags_with_empty_map(self):
        """Test context tags with empty map."""
        config = Config({"namespace": "test", "tags": {}})
        context = Context(config=config)
        self.assertEqual(context.tags, {})

    def test_context_no_tags_specified(self):
        """Test context no tags specified."""
        config = Config({"namespace": "test"})
        context = Context(config=config)
        self.assertEqual(context.tags, {"stacker_namespace": "test"})

    def test_hook_with_sys_path(self):
        """Test hook with sys path."""
        config = Config({
            "namespace": "test",
            "sys_path": "./tests/cfngin",
            "pre_build": [
                {
                    "data_key": "myHook",
                    "path": "fixtures.mock_hooks.mock_hook",
                    "required": True,
                    "args": {
                        "value": "mockResult"}}]})
        load(config)
        context = Context(config=config)
        stage = "pre_build"
        handle_hooks(stage, context.config[stage], "mock-region-1", context)
        self.assertEqual("mockResult", context.hook_data["myHook"]["result"])


class TestFunctions(unittest.TestCase):
    """Test the module level functions."""

    def test_get_fqn_redundant_base(self):
        """Test get fqn redundant base."""
        base = "woot"
        name = "woot-blah"
        self.assertEqual(get_fqn(base, '-', name), name)
        self.assertEqual(get_fqn(base, '', name), name)
        self.assertEqual(get_fqn(base, '_', name), "woot_woot-blah")

    def test_get_fqn_only_base(self):
        """Test get fqn only base."""
        base = "woot"
        self.assertEqual(get_fqn(base, '-'), base)
        self.assertEqual(get_fqn(base, ''), base)
        self.assertEqual(get_fqn(base, '_'), base)

    def test_get_fqn_full(self):
        """Test get fqn full."""
        base = "woot"
        name = "blah"
        self.assertEqual(get_fqn(base, '-', name), "%s-%s" % (base, name))
        self.assertEqual(get_fqn(base, '', name), "%s%s" % (base, name))
        self.assertEqual(get_fqn(base, '_', name), "%s_%s" % (base, name))


if __name__ == '__main__':
    unittest.main()
