"""Tests for runway.cfngin.stack."""

# pyright: basic
import unittest
from typing import Any

from mock import MagicMock

from runway.cfngin.lookups.registry import (
    register_lookup_handler,
    unregister_lookup_handler,
)
from runway.cfngin.stack import Stack
from runway.config import CfnginConfig
from runway.context import CfnginContext
from runway.lookups.handlers.base import LookupHandler

from .factories import generate_definition


class TestStack(unittest.TestCase):
    """Tests for runway.cfngin.stack.Stack."""

    def setUp(self) -> None:
        """Run before tests."""
        self.sd = {"name": "test"}
        self.config = CfnginConfig.parse_obj({"namespace": "namespace"})
        self.context = CfnginContext(config=self.config)
        self.stack = Stack(definition=generate_definition("vpc", 1), context=self.context)

        class FakeLookup(LookupHandler):
            """False Lookup."""

            @classmethod
            def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> str:  # type: ignore
                """Perform the lookup."""
                return "test"

        register_lookup_handler("noop", FakeLookup)

    def tearDown(self) -> None:
        """Run after tests."""
        unregister_lookup_handler("noop")
        return super().tearDown()

    def test_stack_requires(self) -> None:
        """Test stack requires."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={
                "Var1": "${noop fakeStack3::FakeOutput}",
                "Var2": (
                    "some.template.value:${output fakeStack2.FakeOutput}:"
                    "${output fakeStack.FakeOutput}"
                ),
                "Var3": "${output fakeStack.FakeOutput}," "${output fakeStack2.FakeOutput}",
            },
            requires=["fakeStack"],
        )
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(len(stack.requires), 2)
        self.assertIn("fakeStack", stack.requires)
        self.assertIn("fakeStack2", stack.requires)

    def test_stack_requires_circular_ref(self) -> None:
        """Test stack requires circular ref."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={"Var1": "${output vpc-1.FakeOutput}"},
        )
        stack = Stack(definition=definition, context=self.context)
        with self.assertRaises(ValueError):
            stack.requires

    def test_stack_cfn_parameters(self) -> None:
        """Test stack cfn parameters."""
        definition = generate_definition(
            base_name="vpc",
            stack_id=1,
            variables={"Param1": "${output fakeStack.FakeOutput}"},
        )
        stack = Stack(definition=definition, context=self.context)
        stack._blueprint = MagicMock()
        stack._blueprint.parameter_values = {
            "Param2": "Some Resolved Value",
        }
        param = stack.parameter_values["Param2"]
        self.assertEqual(param, "Some Resolved Value")

    def test_stack_tags_default(self) -> None:
        """Test stack tags default."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(base_name="vpc", stack_id=1)
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "prod"})

    def test_stack_tags_override(self) -> None:
        """Test stack tags override."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(base_name="vpc", stack_id=1, tags={"environment": "stage"})
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "stage"})

    def test_stack_tags_extra(self) -> None:
        """Test stack tags extra."""
        self.config.tags = {"environment": "prod"}
        definition = generate_definition(base_name="vpc", stack_id=1, tags={"app": "graph"})
        stack = Stack(definition=definition, context=self.context)
        self.assertEqual(stack.tags, {"environment": "prod", "app": "graph"})


if __name__ == "__main__":
    unittest.main()
