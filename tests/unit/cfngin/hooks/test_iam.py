"""Tests for runway.cfngin.hooks.iam."""
import unittest

import boto3
from awacs.helpers.trust import get_ecs_assumerole_policy
from botocore.exceptions import ClientError
from moto import mock_iam

from runway.cfngin.hooks.iam import _get_cert_arn_from_response, create_ecs_service_role

from ..factories import mock_context, mock_provider

REGION = "us-east-1"

# No test for stacker.hooks.iam.ensure_server_cert_exists until
# updated version of moto is imported
# (https://github.com/spulec/moto/pull/679) merged


class TestIAMHooks(unittest.TestCase):
    """Tests for runway.cfngin.hooks.iam."""

    def setUp(self):
        """Run before tests."""
        self.context = mock_context(namespace="fake")
        self.provider = mock_provider(region=REGION)

    def test_get_cert_arn_from_response(self):
        """Test get cert arn from response."""
        arn = "fake-arn"
        # Creation response
        response = {"ServerCertificateMetadata": {"Arn": arn}}

        self.assertEqual(_get_cert_arn_from_response(response), arn)

        # Existing cert response
        response = {"ServerCertificate": response}
        self.assertEqual(_get_cert_arn_from_response(response), arn)

    def test_create_service_role(self):
        """Test create service role."""
        with mock_iam():
            client = boto3.client("iam", region_name=REGION)

            role_name = "ecsServiceRole"
            with self.assertRaises(ClientError):
                client.get_role(RoleName=role_name)

            self.assertTrue(
                create_ecs_service_role(context=self.context, provider=self.provider,)
            )

            role = client.get_role(RoleName=role_name)

            self.assertIn("Role", role)
            self.assertEqual(role_name, role["Role"]["RoleName"])
            policy_name = "AmazonEC2ContainerServiceRolePolicy"
            client.get_role_policy(RoleName=role_name, PolicyName=policy_name)

    def test_create_service_role_already_exists(self):
        """Test create service role already exists."""
        with mock_iam():
            client = boto3.client("iam", region_name=REGION)
            role_name = "ecsServiceRole"
            client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=get_ecs_assumerole_policy().to_json(),
            )

            self.assertTrue(
                create_ecs_service_role(context=self.context, provider=self.provider,)
            )

            role = client.get_role(RoleName=role_name)

            self.assertIn("Role", role)
            self.assertEqual(role_name, role["Role"]["RoleName"])
            policy_name = "AmazonEC2ContainerServiceRolePolicy"
            client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
