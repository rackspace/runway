"""Tests for runway.cfngin.stack."""
import unittest

from mock import MagicMock

from runway.cfngin.config import Config
from runway.cfngin.context import Context
from runway.cfngin.lookups import register_lookup_handler
from runway.cfngin.stack import Stack

from .factories import generate_definition


class TestStack(unittest.TestCase):
    """Tests for runway.cfngin.stack.Stack."""

    def setUp(self):
        """Run before tests."""
        self.sd = {"name": "test"}  # pylint: disable=invalid-name
        self.config = Config({"namespace": "namespace"})
        self.context = Context(config=self.config)
        self.stack = Stack(
            definition=generate_definition("vpc", 1), context=self.context,
        )
        register_lookup_handler("noop", lambda **kwargs: "test")

    def test_stack_requires(self):
        """Test stack requires."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={
                "Var1": "${noop fakeStack3::FakeOutput}",
                "Var2": (
                    "some.template.value:${output fakeStack2::FakeOutput}:"
                    "${output fakeStack::FakeOutput}"
                ),
                "Var3": "${output fakeStack::FakeOutput},"
                "${output fakeStack2::FakeOutput}",
            },
            requires=["fakeStack"],
        )
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(len(stack.requires), 2)
        self.assertIn(
            "fakeStack", stack.requires,
        )
        self.assertIn(
            "fakeStack2", stack.requires,
        )

    def test_stack_requires_circular_ref(self):
        """Test stack requires circular ref."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={"Var1": "${output vpc.1::FakeOutput}"},
        )
        stack = Stack(definition=definition, context=self.context)
        with self.assertRaises(ValueError):
            stack.requires  # pylint: disable=pointless-statement

    def test_stack_cfn_parameters(self):
        """Test stack cfn parameters."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={"Param1": "${output fakeStack::FakeOutput}"},
        )
        stack = Stack(definition=definition, context=self.context)
        # pylint: disable=protected-access
        stack._blueprint = MagicMock()
        stack._blueprint.get_parameter_values.return_value = {
            "Param2": "Some Resolved Value",
        }
        self.assertEqual(len(stack.parameter_values), 1)
        param = stack.parameter_values["Param2"]
        self.assertEqual(param, "Some Resolved Value")

    def test_stack_tags_default(self):
        """Test stack tags default."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(base_name="vpc", stack_id=1)
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "prod"})

    def test_stack_tags_override(self):
        """Test stack tags override."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(
            base_name="vpc", stack_id=1, tags={"environment": "stage"}
        )
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "stage"})

    def test_stack_tags_extra(self):
        """Test stack tags extra."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(
            base_name="vpc", stack_id=1, tags={"app": "graph"}
        )
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "prod", "app": "graph"})


if __name__ == "__main__":
    unittest.main()
