"""Tests for runway.cfngin.actions.base."""

import unittest
from unittest.mock import MagicMock, PropertyMock, patch

import botocore.exceptions
import pytest

from runway.cfngin.actions.base import BaseAction
from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.exceptions import CfnginBucketNotFound
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
    def version(self) -> str:
        """Return version."""
        return MOCK_VERSION

    def create_template(self) -> None:
        """Create template."""


class TestBaseAction(unittest.TestCase):
    """Tests for runway.cfngin.actions.base.BaseAction."""

    def setUp(self) -> None:
        """Run before tests."""
        self.region = "us-east-1"
        self.session = get_session(self.region)
        self.provider = Provider(self.session)

        self.config_no_persist = {
            "stacks": [
                {"name": "stack1", "template_path": "."},
                {"name": "stack2", "template_path": ".", "requires": ["stack1"]},
            ]
        }

        self.config_persist = {
            "persistent_graph_key": "test.json",
            "stacks": [
                {"name": "stack1", "template_path": "."},
                {"name": "stack2", "template_path": ".", "requires": ["stack1"]},
            ],
        }

    @patch("runway.cfngin.actions.base.ensure_s3_bucket")
    def test_ensure_cfn_bucket_exists(self, mock_ensure_s3_bucket: MagicMock) -> None:
        """Test ensure cfn bucket exists."""
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider=Provider(get_session("us-east-1"))),
        )
        assert not action.ensure_cfn_bucket()
        mock_ensure_s3_bucket.assert_called_once_with(
            action.s3_conn, action.bucket_name, None, create=False
        )

    @patch("runway.cfngin.actions.base.ensure_s3_bucket")
    def test_ensure_cfn_bucket_exists_raise_cfngin_bucket_not_found(
        self, mock_ensure_s3_bucket: MagicMock
    ) -> None:
        """Test ensure cfn bucket exists."""
        mock_ensure_s3_bucket.side_effect = botocore.exceptions.ClientError(
            {},
            "head_bucket",  # type: ignore
        )
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider=Provider(get_session("us-east-1"))),
        )
        with pytest.raises(CfnginBucketNotFound):
            assert action.ensure_cfn_bucket()
        mock_ensure_s3_bucket.assert_called_once_with(
            action.s3_conn, action.bucket_name, None, create=False
        )

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock)
    def test_generate_plan_no_persist_exclude(
        self, mock_stack_action: PropertyMock, mock_tags: PropertyMock
    ) -> None:
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
            provider_builder=MockProviderBuilder(provider=self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=False)

        mock_tags.assert_not_called()
        assert isinstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 2
        assert set() == result_graph_dict["stack1"]
        assert {"stack1"} == result_graph_dict["stack2"]
        assert plan.description == BaseAction.DESCRIPTION
        assert plan.require_unlocked

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock)
    def test_generate_plan_no_persist_include(
        self, mock_stack_action: PropertyMock, mock_tags: PropertyMock
    ) -> None:
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
            provider_builder=MockProviderBuilder(provider=self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=True)

        mock_tags.assert_not_called()
        assert isinstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 2
        assert set() == result_graph_dict["stack1"]
        assert {"stack1"} == result_graph_dict["stack2"]
        assert plan.description == BaseAction.DESCRIPTION
        assert plan.require_unlocked

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock)
    def test_generate_plan_with_persist_exclude(
        self, mock_stack_action: PropertyMock, mock_tags: PropertyMock
    ) -> None:
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
            provider_builder=MockProviderBuilder(provider=self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=False)

        assert isinstance(plan, Plan)
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 2
        assert set() == result_graph_dict["stack1"]
        assert {"stack1"} == result_graph_dict["stack2"]
        assert plan.description == BaseAction.DESCRIPTION
        assert plan.require_unlocked

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock)
    def test_generate_plan_with_persist_include(
        self, mock_stack_action: PropertyMock, mock_tags: PropertyMock
    ) -> None:
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
            provider_builder=MockProviderBuilder(provider=self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=True)

        assert isinstance(plan, Plan)
        mock_tags.assert_called_once()
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 3
        assert set() == result_graph_dict["stack1"]
        assert {"stack1"} == result_graph_dict["stack2"]
        assert set() == result_graph_dict["removed"]
        assert plan.description == BaseAction.DESCRIPTION
        assert plan.require_unlocked

    @patch("runway.context.CfnginContext.persistent_graph_tags", new_callable=PropertyMock)
    @patch("runway.cfngin.actions.base.BaseAction._stack_action", new_callable=PropertyMock)
    def test_generate_plan_with_persist_no_lock_req(
        self, mock_stack_action: PropertyMock, mock_tags: PropertyMock
    ) -> None:
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
            provider_builder=MockProviderBuilder(provider=self.provider, region=self.region),
        )

        plan = action._generate_plan(include_persistent_graph=True, require_unlocked=False)

        assert isinstance(plan, Plan)
        mock_tags.assert_called_once()
        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        assert len(result_graph_dict) == 3
        assert set() == result_graph_dict["stack1"]
        assert {"stack1"} == result_graph_dict["stack2"]
        assert set() == result_graph_dict["removed"]
        assert plan.description == BaseAction.DESCRIPTION
        assert not plan.require_unlocked

    def test_stack_template_url(self) -> None:
        """Test stack template url."""
        context = mock_context("mynamespace")
        blueprint = MockBlueprint(name="test-blueprint", context=context)

        region = "us-east-1"
        endpoint = "https://example.com"
        session = get_session(region)
        provider = Provider(session)
        action = BaseAction(
            context=context,
            provider_builder=MockProviderBuilder(provider=provider, region=region),
        )

        with patch(
            "runway.cfngin.actions.base.get_s3_endpoint",
            autospec=True,
            return_value=endpoint,
        ):
            assert (
                action.stack_template_url(blueprint)
                == f"{endpoint}/cfngin-{context.namespace}-{region}/stack_templates/"
                f"{context.namespace}-{blueprint.name}/{blueprint.name}-{MOCK_VERSION}.json"
            )
