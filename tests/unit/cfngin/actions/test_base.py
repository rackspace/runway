"""Tests for runway.cfngin.actions.base."""
# pylint: disable=no-self-use,protected-access,unused-argument
import unittest

import botocore.exceptions
from botocore.stub import ANY, Stubber
from mock import MagicMock, PropertyMock, patch

from runway.cfngin.actions.base import BaseAction
from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.plan import Graph, Plan, Step
from runway.cfngin.providers.aws.default import Provider
from runway.cfngin.session_cache import get_session

from ..factories import MockProviderBuilder, mock_context

MOCK_VERSION = "01234abcdef"


class MockBlueprint(Blueprint):
    """Test blueprint."""

    VARIABLES = {
        "Param1": {"default": "default", "type": str},
    }

    @property
    def version(self):
        """Return version."""
        return MOCK_VERSION

    def create_template(self):
        """Create template."""


class TestBaseAction(unittest.TestCase):
    """Tests for runway.cfngin.actions.base.BaseAction."""

    def setUp(self):
        """Run before tests."""
        self.region = "us-east-1"
        self.session = get_session(self.region)
        self.provider = Provider(self.session)

        self.config_no_persist = {
            "stacks": [{"name": "stack1"}, {"name": "stack2", "requires": ["stack1"]}]
        }

        self.config_persist = {
            "persistent_graph_key": "test.json",
            "stacks": [{"name": "stack1"}, {"name": "stack2", "requires": ["stack1"]}],
        }

    def test_ensure_cfn_bucket_exists(self):
        """Test ensure cfn bucket exists."""
        session = get_session("us-east-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider),
        )
        stubber = Stubber(action.s3_conn)
        stubber.add_response(
            "head_bucket", service_response={}, expected_params={"Bucket": ANY}
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_bucket_does_not_exist_us_east(self):
        """Test ensure cfn bucket does not exist us east."""
        session = get_session("us-east-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider),
        )
        stubber = Stubber(action.s3_conn)
        stubber.add_client_error(
            "head_bucket",
            service_error_code="NoSuchBucket",
            service_message="Not Found",
            http_status_code=404,
        )
        stubber.add_response(
            "create_bucket", service_response={}, expected_params={"Bucket": ANY}
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_bucket_does_not_exist_us_west(self):
        """Test ensure cfn bucket does not exist us west."""
        session = get_session("us-west-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider, region="us-west-1"),
        )
        stubber = Stubber(action.s3_conn)
        stubber.add_client_error(
            "head_bucket",
            service_error_code="NoSuchBucket",
            service_message="Not Found",
            http_status_code=404,
        )
        stubber.add_response(
            "create_bucket",
            service_response={},
            expected_params={
                "Bucket": ANY,
                "CreateBucketConfiguration": {"LocationConstraint": "us-west-1"},
            },
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_forbidden(self):
        """Test ensure cfn forbidden."""
        session = get_session("us-west-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider),
        )
        stubber = Stubber(action.s3_conn)
        stubber.add_client_error(
            "head_bucket",
            service_error_code="AccessDenied",
            service_message="Forbidden",
            http_status_code=403,
        )
        with stubber:
            with self.assertRaises(botocore.exceptions.ClientError):
                action.ensure_cfn_bucket()

    @patch(
        "runway.cfngin.context.Context._persistent_graph_tags",
        new_callable=PropertyMock,
    )
    @patch(
        "runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock
    )
    def test_generate_plan_no_persist_exclude(self, mock_stack_action, mock_tags):
        """Test generate plan no persist exclude."""
        mock_stack_action.return_value = MagicMock()
        mock_tags.return_value = {}
        context = mock_context(
            namespace="test",
            extra_config_args=self.config_no_persist,
            region=self.region,
        )
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=False)

        mock_tags.assert_not_called()
        self.assertIsInstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(2, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict["stack1"])
        self.assertEqual(set(["stack1"]), result_graph_dict["stack2"])
        self.assertEqual(BaseAction.DESCRIPTION, plan.description)
        self.assertTrue(plan.require_unlocked)

    @patch(
        "runway.cfngin.context.Context._persistent_graph_tags",
        new_callable=PropertyMock,
    )
    @patch(
        "runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock
    )
    def test_generate_plan_no_persist_include(self, mock_stack_action, mock_tags):
        """Test generate plan no persist include."""
        mock_stack_action.return_value = MagicMock()
        mock_tags.return_value = {}
        context = mock_context(
            namespace="test",
            extra_config_args=self.config_no_persist,
            region=self.region,
        )
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=True)

        mock_tags.assert_not_called()
        self.assertIsInstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(2, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict["stack1"])
        self.assertEqual(set(["stack1"]), result_graph_dict["stack2"])
        self.assertEqual(BaseAction.DESCRIPTION, plan.description)
        self.assertTrue(plan.require_unlocked)

    @patch(
        "runway.cfngin.context.Context._persistent_graph_tags",
        new_callable=PropertyMock,
    )
    @patch(
        "runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock
    )
    def test_generate_plan_with_persist_exclude(self, mock_stack_action, mock_tags):
        """Test generate plan with persist exclude."""
        mock_stack_action.return_value = MagicMock()
        mock_tags.return_value = {}
        context = mock_context(
            namespace="test", extra_config_args=self.config_persist, region=self.region
        )
        persist_step = Step.from_stack_name("removed", context)
        context._persistent_graph = Graph.from_steps([persist_step])
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=False)

        self.assertIsInstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(2, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict["stack1"])
        self.assertEqual(set(["stack1"]), result_graph_dict["stack2"])
        self.assertEqual(BaseAction.DESCRIPTION, plan.description)
        self.assertTrue(plan.require_unlocked)

    @patch(
        "runway.cfngin.context.Context._persistent_graph_tags",
        new_callable=PropertyMock,
    )
    @patch(
        "runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock
    )
    def test_generate_plan_with_persist_include(self, mock_stack_action, mock_tags):
        """Test generate plan with persist include."""
        mock_stack_action.return_value = MagicMock()
        mock_tags.return_value = {}
        context = mock_context(
            namespace="test", extra_config_args=self.config_persist, region=self.region
        )
        persist_step = Step.from_stack_name("removed", context)
        context._persistent_graph = Graph.from_steps([persist_step])
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=True)

        self.assertIsInstance(plan, Plan)
        mock_tags.assert_called_once()
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(3, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict["stack1"])
        self.assertEqual(set(["stack1"]), result_graph_dict["stack2"])
        self.assertEqual(set(), result_graph_dict["removed"])
        self.assertEqual(BaseAction.DESCRIPTION, plan.description)
        self.assertTrue(plan.require_unlocked)

    @patch(
        "runway.cfngin.context.Context._persistent_graph_tags",
        new_callable=PropertyMock,
    )
    @patch(
        "runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock
    )
    def test_generate_plan_with_persist_no_lock_req(self, mock_stack_action, mock_tags):
        """Test generate plan with persist no lock req."""
        mock_stack_action.return_value = MagicMock()
        mock_tags.return_value = {}
        context = mock_context(
            namespace="test", extra_config_args=self.config_persist, region=self.region
        )
        persist_step = Step.from_stack_name("removed", context)
        context._persistent_graph = Graph.from_steps([persist_step])
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(self.provider, region=self.region),
        )

        plan = action._generate_plan(
            include_persistent_graph=True, require_unlocked=False
        )

        self.assertIsInstance(plan, Plan)
        mock_tags.assert_called_once()
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(3, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict["stack1"])
        self.assertEqual(set(["stack1"]), result_graph_dict["stack2"])
        self.assertEqual(set(), result_graph_dict["removed"])
        self.assertEqual(BaseAction.DESCRIPTION, plan.description)
        self.assertFalse(plan.require_unlocked)

    def test_stack_template_url(self):
        """Test stack template url."""
        context = mock_context("mynamespace")
        blueprint = MockBlueprint(name="myblueprint", context=context)

        region = "us-east-1"
        endpoint = "https://example.com"
        session = get_session(region)
        provider = Provider(session)
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(provider, region=region),
        )

        with patch(
            "runway.cfngin.actions.base.get_s3_endpoint",
            autospec=True,
            return_value=endpoint,
        ):
            self.assertEqual(
                action.stack_template_url(blueprint),
                "%s/%s/stack_templates/%s/%s-%s.json"
                % (
                    endpoint,
                    "stacker-mynamespace",
                    "mynamespace-myblueprint",
                    "myblueprint",
                    MOCK_VERSION,
                ),
            )
