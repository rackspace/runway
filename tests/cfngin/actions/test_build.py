"""Tests for runway.cfngin.actions.build."""
# pylint: disable=protected-access,unused-argument
import unittest
from collections import namedtuple

import mock

from runway.cfngin import exceptions
from runway.cfngin.actions import build
from runway.cfngin.actions.build import (UsePreviousParameterValue,
                                         _handle_missing_parameters,
                                         _resolve_parameters)
from runway.cfngin.blueprints.variables.types import CFNString
from runway.cfngin.context import Config, Context
from runway.cfngin.exceptions import StackDidNotChange, StackDoesNotExist
from runway.cfngin.providers.aws.default import Provider
from runway.cfngin.providers.base import BaseProvider
from runway.cfngin.session_cache import get_session
from runway.cfngin.status import (COMPLETE, FAILED, PENDING, SKIPPED,
                                  SUBMITTED, NotSubmittedStatus)

from ..factories import MockProviderBuilder, MockThreadingEvent


def mock_stack_parameters(parameters):
    """Mock stack parameters."""
    return {
        'Parameters': [
            {'ParameterKey': k, 'ParameterValue': v}
            for k, v in parameters.items()
        ]
    }


class MockProvider(BaseProvider):
    """Mock provider."""

    def __init__(self, *args, **kwargs):
        """Instantiate class."""
        self._outputs = kwargs.get('outputs', {})

    def set_outputs(self, outputs):
        """Set outputs."""
        self._outputs = outputs

    def get_stack(self, stack_name, *args, **kwargs):
        """Get stack."""
        if stack_name not in self._outputs:
            raise exceptions.StackDoesNotExist(stack_name)
        return {"name": stack_name, "outputs": self._outputs[stack_name]}

    def get_outputs(self, stack_name, *args, **kwargs):
        """Get outputs."""
        stack = self.get_stack(stack_name)
        return stack["outputs"]


class TestBuildAction(unittest.TestCase):
    """Tests for runway.cfngin.actions.build.BuildAction."""

    def setUp(self):
        """Run before tests."""
        self.context = Context(config=Config({"namespace": "namespace"}))
        self.provider = MockProvider()
        self.build_action = build.Action(
            self.context,
            provider_builder=MockProviderBuilder(self.provider))

    def _get_context(self, **kwargs):
        """Get context."""
        config = Config({
            "namespace": "namespace",
            "stacks": [
                {"name": "vpc"},
                {"name": "bastion",
                 "variables": {
                     "test": "${output vpc::something}"}},
                {"name": "db",
                 "variables": {
                     "test": "${output vpc::something}",
                     "else": "${output bastion::something}"}},
                {"name": "other", "variables": {}}
            ],
        })
        return Context(config=config, **kwargs)

    def test_handle_missing_params(self):
        """Test handle missing params."""
        existing_stack_param_dict = {
            "StackName": "teststack",
            "Address": "192.168.0.1"
        }
        existing_stack_params = mock_stack_parameters(
            existing_stack_param_dict
        )
        all_params = existing_stack_param_dict.keys()
        required = ["Address"]
        parameter_values = {"Address": "192.168.0.1"}
        expected_params = {"StackName": UsePreviousParameterValue,
                           "Address": "192.168.0.1"}
        result = _handle_missing_parameters(parameter_values, all_params,
                                            required, existing_stack_params)
        self.assertEqual(sorted(result), sorted(list(expected_params.items())))

    def test_missing_params_no_existing_stack(self):
        """Test missing params no existing stack."""
        all_params = ["Address", "StackName"]
        required = ["Address"]
        parameter_values = {}
        with self.assertRaises(exceptions.MissingParameterException) as result:
            _handle_missing_parameters(parameter_values, all_params, required)

        self.assertEqual(result.exception.parameters, required)

    def test_existing_stack_params_does_not_override_given_params(self):
        """Test existing stack params does not override given params."""
        existing_stack_param_dict = {
            "StackName": "teststack",
            "Address": "192.168.0.1"
        }
        existing_stack_params = mock_stack_parameters(
            existing_stack_param_dict
        )
        all_params = existing_stack_param_dict.keys()
        required = ["Address"]
        parameter_values = {"Address": "10.0.0.1"}
        result = _handle_missing_parameters(parameter_values, all_params,
                                            required, existing_stack_params)
        self.assertEqual(
            sorted(result),
            sorted(list(parameter_values.items()))
        )

    def test_generate_plan(self):
        """Test generate plan."""
        context = self._get_context()
        build_action = build.Action(context, cancel=MockThreadingEvent())
        plan = build_action._generate_plan()
        self.assertEqual(
            {
                'db': set(['bastion', 'vpc']),
                'bastion': set(['vpc']),
                'other': set([]),
                'vpc': set([])},
            plan.graph.to_dict()
        )

    def test_does_not_execute_plan_when_outline_specified(self):
        """Test does not execute plan when outline specified."""
        context = self._get_context()
        build_action = build.Action(context, cancel=MockThreadingEvent())
        with mock.patch.object(build_action, "_generate_plan") as \
                mock_generate_plan:
            build_action.run(outline=True)
            self.assertEqual(mock_generate_plan().execute.call_count, 0)

    def test_execute_plan_when_outline_not_specified(self):
        """Test execute plan when outline not specified."""
        context = self._get_context()
        build_action = build.Action(context, cancel=MockThreadingEvent())
        with mock.patch.object(build_action, "_generate_plan") as \
                mock_generate_plan:
            build_action.run(outline=False)
            self.assertEqual(mock_generate_plan().execute.call_count, 1)

    def test_should_update(self):
        """Test should update."""
        test_scenario = namedtuple("test_scenario",
                                   ["locked", "force", "result"])
        test_scenarios = (
            test_scenario(locked=False, force=False, result=True),
            test_scenario(locked=False, force=True, result=True),
            test_scenario(locked=True, force=False, result=False),
            test_scenario(locked=True, force=True, result=True)
        )
        mock_stack = mock.MagicMock(["locked", "force", "name"])
        mock_stack.name = "test-stack"
        for test in test_scenarios:
            mock_stack.locked = test.locked
            mock_stack.force = test.force
            self.assertEqual(build.should_update(mock_stack), test.result)

    def test_should_ensure_cfn_bucket(self):
        """Test should ensure cfn bucket."""
        test_scenarios = [
            {"outline": False, "dump": False, "result": True},
            {"outline": True, "dump": False, "result": False},
            {"outline": False, "dump": True, "result": False},
            {"outline": True, "dump": True, "result": False},
            {"outline": True, "dump": "DUMP", "result": False}
        ]

        for scenario in test_scenarios:
            outline = scenario["outline"]
            dump = scenario["dump"]
            result = scenario["result"]
            try:
                self.assertEqual(
                    build.should_ensure_cfn_bucket(outline, dump), result)
            except AssertionError as err:
                err.args += ("scenario", str(scenario))
                raise

    def test_should_submit(self):
        """Test should submit."""
        test_scenario = namedtuple("test_scenario",
                                   ["enabled", "result"])
        test_scenarios = (
            test_scenario(enabled=False, result=False),
            test_scenario(enabled=True, result=True),
        )

        mock_stack = mock.MagicMock(["enabled", "name"])
        mock_stack.name = "test-stack"
        for test in test_scenarios:
            mock_stack.enabled = test.enabled
            self.assertEqual(build.should_submit(mock_stack), test.result)


class TestLaunchStack(TestBuildAction):
    """Tests for runway.cfngin.actions.build.BuildAction launch stack."""

    def setUp(self):
        """Run before tests."""
        self.context = self._get_context()
        self.session = get_session(region=None)
        self.provider = Provider(self.session, interactive=False,
                                 recreate_failed=False)
        provider_builder = MockProviderBuilder(self.provider)
        self.build_action = build.Action(self.context,
                                         provider_builder=provider_builder,
                                         cancel=MockThreadingEvent())

        self.stack = mock.MagicMock()
        self.stack.region = None
        self.stack.name = 'vpc'
        self.stack.fqn = 'vpc'
        self.stack.blueprint.rendered = '{}'
        self.stack.locked = False
        self.stack_status = None

        plan = self.build_action._generate_plan()
        self.step = plan.steps[0]
        self.step.stack = self.stack

        def patch_object(*args, **kwargs):
            mock_object = mock.patch.object(*args, **kwargs)
            self.addCleanup(mock_object.stop)
            mock_object.start()

        def get_stack(name, *args, **kwargs):
            if name != self.stack.name or not self.stack_status:
                raise StackDoesNotExist(name)

            return {'StackName': self.stack.name,
                    'StackStatus': self.stack_status,
                    'Outputs': [],
                    'Tags': []}

        def get_events(name, *args, **kwargs):
            return [{'ResourceStatus': 'ROLLBACK_IN_PROGRESS',
                     'ResourceStatusReason': 'CFN fail'}]

        patch_object(self.provider, 'get_stack', side_effect=get_stack)
        patch_object(self.provider, 'update_stack')
        patch_object(self.provider, 'create_stack')
        patch_object(self.provider, 'destroy_stack')
        patch_object(self.provider, 'get_events', side_effect=get_events)

        patch_object(self.build_action, "s3_stack_push")

    def _advance(self, new_provider_status, expected_status, expected_reason):
        """Advance."""
        self.stack_status = new_provider_status
        status = self.step._run_once()
        self.assertEqual(status, expected_status)
        self.assertEqual(status.reason, expected_reason)

    def test_launch_stack_disabled(self):
        """Test launch stack disabled."""
        self.assertEqual(self.step.status, PENDING)

        self.stack.enabled = False
        self._advance(None, NotSubmittedStatus(), "disabled")

    def test_launch_stack_create(self):
        """Test launch stack create."""
        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance(None, SUBMITTED, "creating new stack")

        # status should stay as SUBMITTED when the stack becomes available
        self._advance('CREATE_IN_PROGRESS', SUBMITTED, "creating new stack")

        # status should become COMPLETE once the stack finishes
        self._advance('CREATE_COMPLETE', COMPLETE, "creating new stack")

    def test_launch_stack_create_rollback(self):
        """Test launch stack create rollback."""
        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance(None, SUBMITTED, "creating new stack")

        # provider should now return the CF stack since it exists
        self._advance("CREATE_IN_PROGRESS", SUBMITTED,
                      "creating new stack")

        # rollback should be noticed
        self._advance("ROLLBACK_IN_PROGRESS", SUBMITTED,
                      "rolling back new stack")

        # rollback should not be added twice to the reason
        self._advance("ROLLBACK_IN_PROGRESS", SUBMITTED,
                      "rolling back new stack")

        # rollback should finish with failure
        self._advance("ROLLBACK_COMPLETE", FAILED,
                      "rolled back new stack")

    def test_launch_stack_recreate(self):
        """Test launch stack recreate."""
        self.provider.recreate_failed = True  # pylint: disable=attribute-defined-outside-init

        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # first action with an existing failed stack should be deleting it
        self._advance("ROLLBACK_COMPLETE", SUBMITTED,
                      "destroying stack for re-creation")

        # status should stay as submitted during deletion
        self._advance("DELETE_IN_PROGRESS", SUBMITTED,
                      "destroying stack for re-creation")

        # deletion being complete must trigger re-creation
        self._advance("DELETE_COMPLETE", SUBMITTED,
                      "re-creating stack")

        # re-creation should continue as SUBMITTED
        self._advance("CREATE_IN_PROGRESS", SUBMITTED,
                      "re-creating stack")

        # re-creation should finish with success
        self._advance("CREATE_COMPLETE", COMPLETE,
                      "re-creating stack")

    def test_launch_stack_update_skipped(self):
        """Test launch stack update skipped."""
        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # start the upgrade, that will be skipped
        self.provider.update_stack.side_effect = StackDidNotChange
        self._advance("CREATE_COMPLETE", SKIPPED,
                      "nochange")

    def test_launch_stack_update_rollback(self):
        """Test launch stack update rollback."""
        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance("CREATE_COMPLETE", SUBMITTED,
                      "updating existing stack")

        # update should continue as SUBMITTED
        self._advance("UPDATE_IN_PROGRESS", SUBMITTED,
                      "updating existing stack")

        # rollback should be noticed
        self._advance("UPDATE_ROLLBACK_IN_PROGRESS", SUBMITTED,
                      "rolling back update")

        # rollback should finish with failure
        self._advance("UPDATE_ROLLBACK_COMPLETE", FAILED,
                      "rolled back update")

    def test_launch_stack_update_success(self):
        """Test launch stack update success."""
        # initial status should be PENDING
        self.assertEqual(self.step.status, PENDING)

        # initial run should return SUBMITTED since we've passed off to CF
        self._advance("CREATE_COMPLETE", SUBMITTED,
                      "updating existing stack")

        # update should continue as SUBMITTED
        self._advance("UPDATE_IN_PROGRESS", SUBMITTED,
                      "updating existing stack")

        # update should finish with success
        self._advance("UPDATE_COMPLETE", COMPLETE,
                      "updating existing stack")


class TestFunctions(unittest.TestCase):
    """Tests for runway.cfngin.actions.build module level functions."""

    def setUp(self):
        """Run before tests."""
        self.ctx = Context({"namespace": "test"})
        self.prov = mock.MagicMock()
        self.blueprint = mock.MagicMock()

    def test_resolve_parameters_unused_parameter(self):
        """Test resolve parameters unused parameter."""
        self.blueprint.get_parameter_definitions.return_value = {
            "a": {
                "type": CFNString,
                "description": "A"},
            "b": {
                "type": CFNString,
                "description": "B"}
        }
        params = {"a": "Apple", "c": "Carrot"}
        resolved_params = _resolve_parameters(params, self.blueprint)
        self.assertNotIn("c", resolved_params)
        self.assertIn("a", resolved_params)

    def test_resolve_parameters_none_conversion(self):
        """Test resolve parameters none conversion."""
        self.blueprint.get_parameter_definitions.return_value = {
            "a": {
                "type": CFNString,
                "description": "A"},
            "b": {
                "type": CFNString,
                "description": "B"}
        }
        params = {"a": None, "c": "Carrot"}
        resolved_params = _resolve_parameters(params, self.blueprint)
        self.assertNotIn("a", resolved_params)

    def test_resolve_parameters_booleans(self):
        """Test resolve parameters booleans."""
        self.blueprint.get_parameter_definitions.return_value = {
            "a": {
                "type": CFNString,
                "description": "A"},
            "b": {
                "type": CFNString,
                "description": "B"},
        }
        params = {"a": True, "b": False}
        resolved_params = _resolve_parameters(params, self.blueprint)
        self.assertEqual("true", resolved_params["a"])
        self.assertEqual("false", resolved_params["b"])
