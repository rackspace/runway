"""Tests for runway.cfngin.stack."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import Mock

import pytest

from runway.cfngin.lookups.registry import (
    register_lookup_handler,
    unregister_lookup_handler,
)
from runway.cfngin.stack import Stack
from runway.config import CfnginStackDefinitionModel
from runway.lookups.handlers.base import LookupHandler

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest_mock import MockerFixture

    from ..factories import MockCfnginContext

MODULE = "runway.cfngin.stack"


@pytest.fixture(autouse=True, scope="module")
def fake_lookup() -> Iterator[None]:
    """Register a fake lookup handler for testing."""

    class FakeLookup(LookupHandler):
        """False Lookup."""

        TYPE_NAME: ClassVar[str] = "fake"

        @classmethod
        def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> str:  # type: ignore  # noqa: ARG003
            """Perform the lookup."""
            return "test"

    register_lookup_handler(FakeLookup.TYPE_NAME, FakeLookup)
    yield
    unregister_lookup_handler(FakeLookup.TYPE_NAME)


def generate_stack_definition(
    base_name: str, stack_id: Any = None, **overrides: Any
) -> CfnginStackDefinitionModel:
    """Generate stack definition."""
    definition: dict[str, Any] = {
        "name": f"{base_name}-{stack_id}" if stack_id else base_name,
        "class_path": f"tests.unit.cfngin.fixtures.mock_blueprints.{base_name.upper()}",
        "requires": [],
    }
    definition.update(overrides)
    return CfnginStackDefinitionModel(**definition)


class TestStack:
    """Test Stack."""

    def test_required_by(self, cfngin_context: MockCfnginContext) -> None:
        """Test required_by."""
        stack = Stack(
            definition=generate_stack_definition(
                base_name="vpc",
                required_by=["fakeStack0"],
                variables={"Param1": "${output fakeStack.FakeOutput}"},
            ),
            context=cfngin_context,
        )
        assert stack.required_by == {"fakeStack0"}

    def test_requires(self, cfngin_context: MockCfnginContext) -> None:
        """Test requires."""
        stack = Stack(
            definition=generate_stack_definition(
                base_name="vpc",
                variables={
                    "Var1": "${fake fakeStack2::FakeOutput}",
                    "Var2": (
                        "some.template.value:${output fakeStack1.FakeOutput}:"
                        "${output fakeStack0.FakeOutput}"
                    ),
                    "Var3": "${output fakeStack0.FakeOutput},${output fakeStack1.FakeOutput}",
                },
                requires=["fakeStack0"],
            ),
            context=cfngin_context,
        )
        assert len(stack.requires) == 2
        assert "fakeStack0" in stack.requires
        assert "fakeStack1" in stack.requires

    def test_requires_cyclic_dependency(self, cfngin_context: MockCfnginContext) -> None:
        """Test requires cyclic dependency."""
        stack = Stack(
            definition=generate_stack_definition(
                base_name="vpc",
                variables={"Var1": "${output vpc.FakeOutput}"},
            ),
            context=cfngin_context,
        )
        with pytest.raises(ValueError, match="has a circular reference"):
            assert stack.requires

    def test_resolve(self, cfngin_context: MockCfnginContext, mocker: MockerFixture) -> None:
        """Test resolve."""
        mock_resolve_variables = mocker.patch(f"{MODULE}.resolve_variables")
        mock_provider = Mock()
        stack = Stack(
            definition=generate_stack_definition(base_name="vpc"),
            context=cfngin_context,
        )
        stack._blueprint = Mock()
        assert not stack.resolve(cfngin_context, mock_provider)
        mock_resolve_variables.assert_called_once_with(
            stack.variables, cfngin_context, mock_provider
        )
        stack._blueprint.resolve_variables.assert_called_once_with(stack.variables)

    def test_set_outputs(self, cfngin_context: MockCfnginContext) -> None:
        """Test set_outputs."""
        stack = Stack(
            definition=generate_stack_definition(base_name="vpc"),
            context=cfngin_context,
        )
        assert not stack.outputs
        outputs = {"foo": "bar"}
        assert not stack.set_outputs(outputs)
        assert stack.outputs == outputs

    def test_stack_policy(self, cfngin_context: MockCfnginContext, tmp_path: Path) -> None:
        """Test stack_policy."""
        stack_policy_path = tmp_path / "stack_policy.json"
        stack_policy_path.write_text("success")
        assert (
            Stack(
                definition=generate_stack_definition(
                    base_name="vpc", stack_policy_path=stack_policy_path
                ),
                context=cfngin_context,
            ).stack_policy
            == "success"
        )

    def test_stack_policy_not_provided(self, cfngin_context: MockCfnginContext) -> None:
        """Test stack_policy."""
        assert not Stack(
            definition=generate_stack_definition(base_name="vpc"),
            context=cfngin_context,
        ).stack_policy

    def test_tags(self, cfngin_context: MockCfnginContext) -> None:
        """Test tags."""
        cfngin_context.config.tags = {"environment": "prod"}
        assert Stack(
            definition=generate_stack_definition(
                base_name="vpc", tags={"app": "graph", "environment": "stage"}
            ),
            context=cfngin_context,
        ).tags == {"app": "graph", "environment": "stage"}

    def test_tags_default(self, cfngin_context: MockCfnginContext) -> None:
        """Test tags."""
        cfngin_context.config.tags = {"environment": "prod"}
        assert Stack(
            definition=generate_stack_definition(base_name="vpc"),
            context=cfngin_context,
        ).tags == {"environment": "prod"}

    @pytest.mark.parametrize(
        "termination_protection, expected",
        [(False, False), (True, True)],
    )
    def test_termination_protection(
        self,
        cfngin_context: MockCfnginContext,
        expected: str,
        termination_protection: bool | str,
    ) -> None:
        """Test termination_protection."""
        assert (
            Stack(
                definition=generate_stack_definition(
                    base_name="vpc", termination_protection=termination_protection
                ),
                context=cfngin_context,
            ).termination_protection
            is expected
        )
