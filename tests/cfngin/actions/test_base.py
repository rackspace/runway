"""Tests for runway.cfngin.actions.base."""
import unittest

import botocore.exceptions
from botocore.stub import ANY, Stubber
import mock

from runway.cfngin.actions.base import BaseAction
from runway.cfngin.blueprints.base import Blueprint
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

    def test_ensure_cfn_bucket_exists(self):
        """Test ensure cfn bucket exists."""
        session = get_session("us-east-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider)
        )
        stubber = Stubber(action.s3_conn)
        stubber.add_response(
            "head_bucket",
            service_response={},
            expected_params={
                "Bucket": ANY,
            }
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_bucket_does_not_exist_us_east(self):
        """Test ensure cfn bucket does not exist us east."""
        session = get_session("us-east-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider)
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
            }
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_bucket_does_not_exist_us_west(self):
        """Test ensure cfn bucket does not exist us west."""
        session = get_session("us-west-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider, region="us-west-1")
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
                "CreateBucketConfiguration": {
                    "LocationConstraint": "us-west-1",
                }
            }
        )
        with stubber:
            action.ensure_cfn_bucket()

    def test_ensure_cfn_forbidden(self):
        """Test ensure cfn forbidden."""
        session = get_session("us-west-1")
        provider = Provider(session)
        action = BaseAction(
            context=mock_context("mynamespace"),
            provider_builder=MockProviderBuilder(provider)
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
            provider_builder=MockProviderBuilder(provider, region=region)
        )

        with mock.patch('runway.cfngin.actions.base.get_s3_endpoint',
                        autospec=True, return_value=endpoint):
            self.assertEqual(
                action.stack_template_url(blueprint),
                "%s/%s/stack_templates/%s/%s-%s.json" % (
                    endpoint,
                    "stacker-mynamespace",
                    "mynamespace-myblueprint",
                    "myblueprint",
                    MOCK_VERSION
                )
            )
