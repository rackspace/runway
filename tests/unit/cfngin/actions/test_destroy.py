"""Tests for runway.cfngin.actions.destroy."""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

from runway.cfngin.actions import destroy
from runway.cfngin.exceptions import StackDoesNotExist
from runway.cfngin.plan import Graph, Step
from runway.cfngin.status import COMPLETE, PENDING, SKIPPED, SUBMITTED, FailedStatus
from runway.config import CfnginConfig
from runway.context import CfnginContext

from ..factories import MockProviderBuilder, MockThreadingEvent


class MockStack:
    """Mock our local CFNgin stack and an AWS provider stack."""

    def __init__(self, name: str, *_args: Any, **_kwargs: Any) -> None:
        """Instantiate class."""
        self.name = name
        self.fqn = name
        self.region = None
        self.profile = None
        self.requires = []


class TestDestroyAction(unittest.TestCase):
    """Tests for runway.cfngin.actions.destroy.DestroyAction."""

    def setUp(self) -> None:
        """Run before tests."""
        self.context = self._get_context()
        self.action = destroy.Action(self.context, cancel=MockThreadingEvent())  # type: ignore

    def _get_context(
        self, extra_config_args: dict[str, Any] | None = None, **kwargs: Any
    ) -> CfnginContext:
        """Get context."""
        config = {
            "namespace": "namespace",
            "stacks": [
                {"name": "vpc", "template_path": "."},
                {"name": "bastion", "requires": ["vpc"], "template_path": "."},
                {
                    "name": "instance",
                    "requires": ["vpc", "bastion"],
                    "template_path": ".",
                },
                {
                    "name": "db",
                    "requires": ["instance", "vpc", "bastion"],
                    "template_path": ".",
                },
                {"name": "other", "requires": ["db"], "template_path": "."},
            ],
        }
        if extra_config_args:
            config.update(extra_config_args)
        return CfnginContext(config=CfnginConfig.parse_obj(config), **kwargs)

    def test_generate_plan(self) -> None:
        """Test generate plan."""
        plan = self.action._generate_plan(reverse=True)
        assert plan.graph.to_dict() == {
            "vpc": {"db", "instance", "bastion"},
            "other": set(),
            "bastion": {"instance", "db"},
            "instance": {"db"},
            "db": {"other"},
        }

    def test_only_execute_plan_when_forced(self) -> None:
        """Test only execute plan when forced."""
        with patch.object(self.action, "_generate_plan") as mock_generate_plan:
            self.action.run(force=False)
            assert mock_generate_plan().execute.call_count == 0

    def test_execute_plan_when_forced(self) -> None:
        """Test execute plan when forced."""
        with patch.object(self.action, "_generate_plan") as mock_generate_plan:
            self.action.run(force=True)
            assert mock_generate_plan().execute.call_count == 1

    def test_destroy_stack_complete_if_state_submitted(self) -> None:
        """Test destroy stack complete if state submitted."""
        # Simulate the provider not being able to find the stack (a result of
        # it being successfully deleted)
        provider = MagicMock()
        provider.get_stack.side_effect = StackDoesNotExist("mock")
        self.action.provider_builder = MockProviderBuilder(provider=provider)
        status = self.action._destroy_stack(MockStack("vpc"), status=PENDING)  # type: ignore
        # if we haven't processed the step (ie. has never been SUBMITTED,
        # should be skipped)
        assert status == SKIPPED
        status = self.action._destroy_stack(MockStack("vpc"), status=SUBMITTED)  # type: ignore
        # if we have processed the step and then can't find the stack, it means
        # we successfully deleted it
        assert status == COMPLETE

    def test_destroy_stack_delete_failed(self) -> None:
        """Test _destroy_stack DELETE_FAILED."""
        provider = MagicMock()
        provider.get_stack.return_value = {
            "StackName": "test",
            "StackStatus": "DELETE_FAILED",
            "StackStatusReason": "reason",
        }
        provider.is_stack_destroyed.return_value = False
        provider.is_stack_in_progress.return_value = False
        provider.is_stack_destroy_possible.return_value = False
        provider.get_stack_status_reason.return_value = "reason"
        self.action.provider_builder = MockProviderBuilder(provider=provider)
        status = self.action._destroy_stack(MockStack("vpc"), status=PENDING)  # type: ignore
        provider.is_stack_destroyed.assert_called_once_with(provider.get_stack.return_value)
        provider.is_stack_in_progress.assert_called_once_with(provider.get_stack.return_value)
        provider.is_stack_destroy_possible.assert_called_once_with(provider.get_stack.return_value)
        provider.get_delete_failed_status_reason.assert_called_once_with("vpc")
        provider.get_stack_status_reason.assert_called_once_with(provider.get_stack.return_value)
        assert isinstance(status, FailedStatus)
        assert status.reason == "reason"

    def test_destroy_stack_step_statuses(self) -> None:
        """Test destroy stack step statuses."""
        mock_provider = MagicMock()
        stacks_dict = self.context.stacks_dict

        def get_stack(stack_name: Any) -> Any:
            return stacks_dict.get(stack_name)

        plan = self.action._generate_plan()
        step = plan.steps[0]
        # we need the AWS provider to generate the plan, but swap it for
        # the mock one to make the test easier
        self.action.provider_builder = MockProviderBuilder(provider=mock_provider)

        # simulate stack doesn't exist and we haven't submitted anything for
        # deletion
        mock_provider.get_stack.side_effect = StackDoesNotExist("mock")

        step.run()
        assert step.status == SKIPPED

        # simulate stack getting successfully deleted
        mock_provider.get_stack.side_effect = get_stack
        mock_provider.is_stack_destroyed.return_value = False
        mock_provider.is_stack_in_progress.return_value = False

        step._run_once()
        assert step.status == SUBMITTED
        mock_provider.is_stack_destroyed.return_value = False
        mock_provider.is_stack_in_progress.return_value = True

        step._run_once()
        assert step.status == SUBMITTED
        mock_provider.is_stack_destroyed.return_value = True
        mock_provider.is_stack_in_progress.return_value = False

        step._run_once()
        assert step.status == COMPLETE

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.context.CfnginContext.lock_persistent_graph", new_callable=MagicMock)
    @patch("runway.context.CfnginContext.unlock_persistent_graph", new_callable=MagicMock)
    @patch("runway.cfngin.plan.Plan.execute", new_callable=MagicMock)
    def test_run_persist(
        self,
        mock_execute: MagicMock,
        mock_unlock: MagicMock,
        mock_lock: MagicMock,
        mock_graph_tags: PropertyMock,
    ) -> None:
        """Test run persist."""
        mock_graph_tags.return_value = {}
        context = self._get_context(extra_config_args={"persistent_graph_key": "test.json"})
        context._persistent_graph = Graph.from_steps([Step.from_stack_name("removed", context)])
        destroy_action = destroy.Action(context=context)
        destroy_action.run(force=True)

        mock_graph_tags.assert_called_once()
        mock_lock.assert_called_once()
        mock_execute.assert_called_once()
        mock_unlock.assert_called_once()
