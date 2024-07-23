"""Tests for runway.cfngin.actions.deploy."""

from __future__ import annotations

import unittest
from collections import namedtuple
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from runway.cfngin import exceptions
from runway.cfngin.actions import deploy
from runway.cfngin.actions.deploy import (
    Action,
    UsePreviousParameterValue,
    _handle_missing_parameters,
    _resolve_parameters,
)
from runway.cfngin.blueprints.variables.types import CFNString
from runway.cfngin.exceptions import (
    CfnginBucketRequired,
    StackDidNotChange,
    StackDoesNotExist,
)
from runway.cfngin.plan import Graph, Plan, Step
from runway.cfngin.providers.aws.default import Provider
from runway.cfngin.providers.base import BaseProvider
from runway.cfngin.session_cache import get_session
from runway.cfngin.status import (
    COMPLETE,
    FAILED,
    PENDING,
    SKIPPED,
    SUBMITTED,
    FailedStatus,
    NotSubmittedStatus,
)
from runway.config import CfnginConfig
from runway.context import CfnginContext

from ..factories import MockProviderBuilder, MockThreadingEvent

if TYPE_CHECKING:
    from mypy_boto3_cloudformation.type_defs import StackTypeDef
    from pytest_mock import MockerFixture

    from runway.cfngin.status import Status


def mock_stack_parameters(parameters: dict[str, Any]) -> StackTypeDef:
    """Mock stack parameters."""
    return {  # type: ignore
        "Parameters": [{"ParameterKey": k, "ParameterValue": v} for k, v in parameters.items()]
    }


class MockProvider(BaseProvider):
    """Mock provider."""

    _outputs: dict[str, dict[str, str]]

    def __init__(self, *, outputs: dict[str, dict[str, str]] | None = None, **_: Any) -> None:
        """Instantiate class."""
        self._outputs = outputs or {}

    def set_outputs(self, outputs: dict[str, dict[str, str]]) -> None:
        """Set outputs."""
        self._outputs = outputs

    def get_stack(
        self, stack_name: str, *_args: Any, **_kwargs: Any
    ) -> dict[str, dict[str, str] | str]:
        """Get stack."""
        if stack_name not in self._outputs:
            raise exceptions.StackDoesNotExist(stack_name)
        return {"name": stack_name, "outputs": self._outputs[stack_name]}

    def get_outputs(self, stack_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        """Get outputs."""
        stack = self.get_stack(stack_name)
        return stack["outputs"]  # type: ignore


class MockStack:
    """Mock our local CFNgin stack and an AWS provider stack."""

    def __init__(
        self,
        name: str,
        in_progress_behavior: str | None = None,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        """Instantiate class."""
        self.name = name
        self.fqn = name
        self.in_progress_behavior = in_progress_behavior
        self.region = None
        self.profile = None
        self.requires = []


class TestAction:
    """Test Action."""

    @pytest.mark.parametrize(
        "bucket_name, explicit, expected",
        [
            (None, False, True),
            (None, True, True),
            ("something", False, False),
            ("something", True, True),
        ],
    )
    def test_upload_disabled(
        self,
        bucket_name: Optional[str],
        cfngin_context: CfnginContext,
        explicit: bool,
        expected: bool,
        mocker: MockerFixture,
    ) -> None:
        """Test upload_disabled."""
        mocker.patch.object(cfngin_context, "bucket_name", bucket_name)
        obj = Action(cfngin_context)
        obj.upload_explicitly_disabled = explicit
        assert obj.upload_disabled is expected

    def test_upload_disabled_setter(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test upload_disabled."""
        mocker.patch.object(cfngin_context, "bucket_name", "something")
        obj = Action(cfngin_context)
        obj.upload_disabled = False
        assert not obj.upload_disabled
        assert not obj.upload_explicitly_disabled

        obj.upload_disabled = True
        assert obj.upload_disabled
        assert obj.upload_explicitly_disabled

    def test_upload_disabled_setter_raise_cfngin_bucket_required(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test upload_disabled."""
        mocker.patch.object(cfngin_context, "bucket_name", None)
        with pytest.raises(CfnginBucketRequired):
            Action(cfngin_context).upload_disabled = False


class TestBuildAction(unittest.TestCase):  # TODO (kyle): refactor tests into the TestAction class
    """Tests for runway.cfngin.actions.deploy.BuildAction."""

    def setUp(self) -> None:
        """Run before tests."""
        self.context = CfnginContext(config=CfnginConfig.parse_obj({"namespace": "namespace"}))
        self.provider = MockProvider()
        self.deploy_action = deploy.Action(
            self.context,
            provider_builder=MockProviderBuilder(provider=self.provider),  # type: ignore
        )

    def _get_context(
        self, extra_config_args: Optional[dict[str, Any]] = None, **kwargs: Any
    ) -> CfnginContext:
        """Get context."""
        config: dict[str, Any] = {
            "namespace": "namespace",
            "stacks": [
                {"name": "vpc", "template_path": "."},
                {
                    "name": "bastion",
                    "template_path": ".",
                    "variables": {"test": "${output vpc.something}"},
                },
                {
                    "name": "db",
                    "template_path": ".",
                    "variables": {
                        "test": "${output vpc.something}",
                        "else": "${output bastion.something}",
                    },
                },
                {"name": "other", "template_path": ".", "variables": {}},
            ],
        }
        if extra_config_args:
            config.update(extra_config_args)
        return CfnginContext(config=CfnginConfig.parse_obj(config), **kwargs)

    def test_destroy_stack_delete_failed(self) -> None:
        """Test _destroy_stack DELETE_FAILED."""
        provider = MagicMock()
        provider.get_stack.return_value = {
            "StackName": "test",
            "StackStatus": "DELETE_FAILED",
            "StackStatusReason": "reason",
        }
        provider.is_stack_being_destroyed.return_value = False
        provider.is_stack_destroyed.return_value = False
        provider.is_stack_in_progress.return_value = False
        provider.is_stack_destroy_possible.return_value = False
        provider.get_stack_status_reason.return_value = "reason"
        self.deploy_action.provider_builder = MockProviderBuilder(provider=provider)
        status = self.deploy_action._destroy_stack(
            MockStack("vpc", in_progress_behavior="wait"), status=PENDING  # type: ignore
        )
        provider.is_stack_being_destroyed.assert_called_once_with(provider.get_stack.return_value)
        provider.is_stack_destroyed.assert_called_once_with(provider.get_stack.return_value)
        provider.is_stack_in_progress.assert_called_once_with(provider.get_stack.return_value)
        provider.is_stack_destroy_possible.assert_called_once_with(provider.get_stack.return_value)
        provider.get_delete_failed_status_reason.assert_called_once_with("vpc")
        provider.get_stack_status_reason.assert_called_once_with(provider.get_stack.return_value)
        assert isinstance(status, FailedStatus)
        assert status.reason == "reason"

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    def test_generate_plan_persist_destroy(self, mock_graph_tags: PropertyMock) -> None:
        """Test generate plan persist destroy."""
        mock_graph_tags.return_value = {}
        context = self._get_context(extra_config_args={"persistent_graph_key": "test.json"})
        context._persistent_graph = Graph.from_steps([Step.from_stack_name("removed", context)])
        deploy_action = deploy.Action(context=context)
        plan = cast(Plan, deploy_action._Action__generate_plan())  # type: ignore

        assert isinstance(plan, Plan)
        assert plan.description == deploy.Action.DESCRIPTION
        mock_graph_tags.assert_called_once()
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 5
        assert set() == result_graph_dict["other"]
        assert set() == result_graph_dict["removed"]
        assert set() == result_graph_dict["vpc"]
        assert {"vpc"} == result_graph_dict["bastion"]
        assert {"bastion", "vpc"} == result_graph_dict["db"]
        assert deploy_action._destroy_stack == plan.graph.steps["removed"].fn
        assert deploy_action._launch_stack == plan.graph.steps["vpc"].fn
        assert deploy_action._launch_stack == plan.graph.steps["bastion"].fn
        assert deploy_action._launch_stack == plan.graph.steps["db"].fn
        assert deploy_action._launch_stack == plan.graph.steps["other"].fn

    def test_handle_missing_params(self) -> None:
        """Test handle missing params."""
        existing_stack_param_dict = {"StackName": "teststack", "Address": "192.168.0.1"}
        existing_stack_params = mock_stack_parameters(existing_stack_param_dict)
        all_params = list(existing_stack_param_dict.keys())
        required = ["Address"]
        parameter_values = {"Address": "192.168.0.1"}
        expected_params = {
            "StackName": UsePreviousParameterValue,
            "Address": "192.168.0.1",
        }
        result = _handle_missing_parameters(
            parameter_values, all_params, required, existing_stack_params
        )
        assert sorted(result) == sorted(expected_params.items())

    def test_missing_params_no_existing_stack(self) -> None:
        """Test missing params no existing stack."""
        all_params = ["Address", "StackName"]
        required = ["Address"]
        parameter_values: dict[str, Any] = {}
        with pytest.raises(exceptions.MissingParameterException) as result:
            _handle_missing_parameters(parameter_values, all_params, required)

        assert result.value.parameters == required

    def test_existing_stack_params_does_not_override_given_params(self) -> None:
        """Test existing stack params does not override given params."""
        existing_stack_param_dict = {"StackName": "teststack", "Address": "192.168.0.1"}
        existing_stack_params = mock_stack_parameters(existing_stack_param_dict)
        all_params = list(existing_stack_param_dict.keys())
        required = ["Address"]
        parameter_values = {"Address": "10.0.0.1"}
        result = _handle_missing_parameters(
            parameter_values, all_params, required, existing_stack_params
        )
        assert sorted(result) == sorted(parameter_values.items())

    def test_generate_plan(self) -> None:
        """Test generate plan."""
        context = self._get_context()
        deploy_action = deploy.Action(context, cancel=MockThreadingEvent())  # type: ignore
        plan = cast(Plan, deploy_action._Action__generate_plan())  # type: ignore
        assert plan.graph.to_dict() == {
            "db": {"bastion", "vpc"},
            "bastion": {"vpc"},
            "other": set(),
            "vpc": set(),
        }

    def test_does_not_execute_plan_when_outline_specified(self) -> None:
        """Test does not execute plan when outline specified."""
        context = self._get_context()
        deploy_action = deploy.Action(context, cancel=MockThreadingEvent())  # type: ignore
        with patch.object(deploy_action, "_generate_plan") as mock_generate_plan:
            deploy_action.run(outline=True)
            assert mock_generate_plan().execute.call_count == 0

    def test_execute_plan_when_outline_not_specified(self) -> None:
        """Test execute plan when outline not specified."""
        context = self._get_context()
        deploy_action = deploy.Action(context, cancel=MockThreadingEvent())  # type: ignore
        with patch.object(deploy_action, "_generate_plan") as mock_generate_plan:
            deploy_action.run(outline=False)
            assert mock_generate_plan().execute.call_count == 1

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
        deploy_action = deploy.Action(context=context)
        deploy_action.run()

        mock_graph_tags.assert_called_once()
        mock_lock.assert_called_once()
        mock_execute.assert_called_once()
        mock_unlock.assert_called_once()

    def test_should_update(self) -> None:
        """Test should update."""
        test_scenario = namedtuple("test_scenario", ["locked", "force", "result"])  # type: ignore
        test_scenarios = (
            test_scenario(locked=False, force=False, result=True),
            test_scenario(locked=False, force=True, result=True),
            test_scenario(locked=True, force=False, result=False),
            test_scenario(locked=True, force=True, result=True),
        )
        mock_stack = MagicMock(["locked", "force", "name"])
        mock_stack.name = "test-stack"
        for test in test_scenarios:
            mock_stack.locked = test.locked
            mock_stack.force = test.force
            assert deploy.should_update(mock_stack) == test.result  # type: ignore

    def test_should_ensure_cfn_bucket(self) -> None:
        """Test should ensure cfn bucket."""
        test_scenarios = [
            {"outline": False, "dump": False, "result": True},
            {"outline": True, "dump": False, "result": False},
            {"outline": False, "dump": True, "result": False},
            {"outline": True, "dump": True, "result": False},
            {"outline": True, "dump": "DUMP", "result": False},
        ]

        for scenario in test_scenarios:
            outline = scenario["outline"]
            dump = scenario["dump"]
            result = scenario["result"]
            try:
                assert deploy.should_ensure_cfn_bucket(outline, dump) == result  # type: ignore
            except AssertionError as err:
                err.args += ("scenario", str(scenario))
                raise

    def test_should_submit(self) -> None:
        """Test should submit."""
        test_scenario = namedtuple("test_scenario", ["enabled", "result"])  # type: ignore
        test_scenarios = (
            test_scenario(enabled=False, result=False),
            test_scenario(enabled=True, result=True),
        )

        mock_stack = MagicMock(["enabled", "name"])
        mock_stack.name = "test-stack"
        for test in test_scenarios:
            mock_stack.enabled = test.enabled
            assert deploy.should_submit(mock_stack) == test.result  # type: ignore


class TestLaunchStack(TestBuildAction):  # TODO (kyle): refactor tests to be pytest tests
    """Tests for runway.cfngin.actions.deploy.BuildAction launch stack."""

    def setUp(self) -> None:
        """Run before tests."""
        self.context = self._get_context()
        self.session = get_session(region=None)
        self.provider = Provider(self.session, interactive=False, recreate_failed=False)
        provider_builder = MockProviderBuilder(provider=self.provider)
        self.deploy_action = deploy.Action(
            self.context,
            provider_builder=provider_builder,
            cancel=MockThreadingEvent(),  # type: ignore
        )

        self.stack = MagicMock()
        self.stack.region = None
        self.stack.name = "vpc"
        self.stack.fqn = "vpc"
        self.stack.blueprint.rendered = "{}"
        self.stack.locked = False
        self.stack_status = None

        plan = cast(Plan, self.deploy_action._Action__generate_plan())  # type: ignore
        self.step = plan.steps[0]
        self.step.stack = self.stack

        def patch_object(*args: Any, **kwargs: Any) -> None:
            mock_object = patch.object(*args, **kwargs)
            self.addCleanup(mock_object.stop)
            mock_object.start()

        def get_stack(name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            if name != self.stack.name or not self.stack_status:
                raise StackDoesNotExist(name)

            return {
                "StackName": self.stack.name,
                "StackStatus": self.stack_status,
                "Outputs": [],
                "Tags": [],
            }

        def get_events(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
            return [
                {
                    "ResourceStatus": "ROLLBACK_IN_PROGRESS",
                    "ResourceStatusReason": "CFN fail",
                    "Timestamp": datetime(2015, 1, 1),
                }
            ]

        patch_object(self.provider, "get_stack", side_effect=get_stack)
        patch_object(self.provider, "update_stack")
        patch_object(self.provider, "create_stack")
        patch_object(self.provider, "destroy_stack")
        patch_object(self.provider, "get_events", side_effect=get_events)

        patch_object(self.deploy_action, "s3_stack_push")

    def _advance(
        self,
        new_provider_status: Optional[str],
        expected_status: Optional[Status],
        expected_reason: str,
    ) -> None:
        """Advance."""
        self.stack_status = new_provider_status
        status = self.step._run_once()
        assert status == expected_status
        assert status.reason == expected_reason

    def test_launch_stack_disabled(self) -> None:
        """Test launch stack disabled."""
        assert self.step.status == PENDING

        self.stack.enabled = False
        self._advance(None, NotSubmittedStatus(), "disabled")

    def test_launch_stack_create(self) -> None:
        """Test launch stack create."""
        # initial status should be PENDING
        assert self.step.status == PENDING

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance(None, SUBMITTED, "creating new stack")

        # status should stay as SUBMITTED when the stack becomes available
        self._advance("CREATE_IN_PROGRESS", SUBMITTED, "creating new stack")

        # status should become COMPLETE once the stack finishes
        self._advance("CREATE_COMPLETE", COMPLETE, "creating new stack")

    def test_launch_stack_create_rollback(self) -> None:
        """Test launch stack create rollback."""
        # initial status should be PENDING
        assert self.step.status == PENDING

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance(None, SUBMITTED, "creating new stack")

        # provider should now return the CF stack since it exists
        self._advance("CREATE_IN_PROGRESS", SUBMITTED, "creating new stack")

        # rollback should be noticed
        self._advance("ROLLBACK_IN_PROGRESS", SUBMITTED, "rolling back new stack")

        # rollback should not be added twice to the reason
        self._advance("ROLLBACK_IN_PROGRESS", SUBMITTED, "rolling back new stack")

        # rollback should finish with failure
        self._advance("ROLLBACK_COMPLETE", FAILED, "rolled back new stack")

    def test_launch_stack_recreate(self) -> None:
        """Test launch stack recreate."""
        self.provider.recreate_failed = True

        # initial status should be PENDING
        assert self.step.status == PENDING

        # first action with an existing failed stack should be deleting it
        self._advance("ROLLBACK_COMPLETE", SUBMITTED, "destroying stack for re-creation")

        # status should stay as submitted during deletion
        self._advance("DELETE_IN_PROGRESS", SUBMITTED, "destroying stack for re-creation")

        # deletion being complete must trigger re-creation
        self._advance("DELETE_COMPLETE", SUBMITTED, "re-creating stack")

        # re-creation should continue as SUBMITTED
        self._advance("CREATE_IN_PROGRESS", SUBMITTED, "re-creating stack")

        # re-creation should finish with success
        self._advance("CREATE_COMPLETE", COMPLETE, "re-creating stack")

    def test_launch_stack_update_skipped(self) -> None:
        """Test launch stack update skipped."""
        # initial status should be PENDING
        assert self.step.status == PENDING

        # start the upgrade, that will be skipped
        self.provider.update_stack.side_effect = StackDidNotChange  # type: ignore
        self._advance("CREATE_COMPLETE", SKIPPED, "nochange")

    def test_launch_stack_update_rollback(self) -> None:
        """Test launch stack update rollback."""
        # initial status should be PENDING
        assert self.step.status == PENDING

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance("CREATE_COMPLETE", SUBMITTED, "updating existing stack")

        # update should continue as SUBMITTED
        self._advance("UPDATE_IN_PROGRESS", SUBMITTED, "updating existing stack")

        # rollback should be noticed
        self._advance("UPDATE_ROLLBACK_IN_PROGRESS", SUBMITTED, "rolling back update")

        # rollback should finish with failure
        self._advance("UPDATE_ROLLBACK_COMPLETE", FAILED, "rolled back update")

    def test_launch_stack_update_success(self) -> None:
        """Test launch stack update success."""
        # initial status should be PENDING
        assert self.step.status == PENDING

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance("CREATE_COMPLETE", SUBMITTED, "updating existing stack")

        # update should continue as SUBMITTED
        self._advance("UPDATE_IN_PROGRESS", SUBMITTED, "updating existing stack")

        # update should finish with success
        self._advance("UPDATE_COMPLETE", COMPLETE, "updating existing stack")


class TestFunctions(unittest.TestCase):  # TODO (kyle): refactor tests to be pytest tests
    """Tests for runway.cfngin.actions.deploy module level functions."""

    def setUp(self) -> None:
        """Run before tests."""
        self.ctx = CfnginContext()
        self.prov = MagicMock()
        self.blueprint = MagicMock()

    def test_resolve_parameters_unused_parameter(self) -> None:
        """Test resolve parameters unused parameter."""
        self.blueprint.parameter_definitions = {
            "a": {"type": CFNString, "description": "A"},
            "b": {"type": CFNString, "description": "B"},
        }
        params = {"a": "Apple", "c": "Carrot"}
        resolved_params = _resolve_parameters(params, self.blueprint)
        assert "c" not in resolved_params
        assert "a" in resolved_params

    def test_resolve_parameters_none_conversion(self) -> None:
        """Test resolve parameters none conversion."""
        self.blueprint.parameter_definitions = {
            "a": {"type": CFNString, "description": "A"},
            "b": {"type": CFNString, "description": "B"},
        }
        params = {"a": None, "c": "Carrot"}
        resolved_params = _resolve_parameters(params, self.blueprint)
        assert "a" not in resolved_params

    def test_resolve_parameters_booleans(self) -> None:
        """Test resolve parameters booleans."""
        self.blueprint.parameter_definitions = {
            "a": {"type": CFNString, "description": "A"},
            "b": {"type": CFNString, "description": "B"},
        }
        params = {"a": True, "b": False}
        resolved_params = _resolve_parameters(params, self.blueprint)
        assert resolved_params["a"] == "true"
        assert resolved_params["b"] == "false"
