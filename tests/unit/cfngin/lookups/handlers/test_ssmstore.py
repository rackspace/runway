"""Tests for runway.cfngin.lookups.handlers.ssmstore."""
import unittest

import boto3
import mock
from botocore.stub import Stubber
from six import string_types

from runway.cfngin.lookups.handlers.ssmstore import SsmstoreLookup

from ...factories import SessionStub


class TestSSMStoreHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.ssmstore.SsmstoreLookup."""

    client = boto3.client(
        "ssm",
        region_name="us-east-1",
        # bypass the need to have these in the env
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )

    def setUp(self):
        """Run before tests."""
        self.stubber = Stubber(self.client)
        self.get_parameters_response = {
            "Parameters": [{"Name": "ssmkey", "Type": "String", "Value": "ssmvalue"}],
            "InvalidParameters": ["invalid_ssm_param"],
        }
        self.invalid_get_parameters_response = {"InvalidParameters": ["ssmkey"]}
        self.expected_params = {"Names": ["ssmkey"], "WithDecryption": True}
        self.ssmkey = "ssmkey"
        self.ssmvalue = "ssmvalue"

    @mock.patch(
        "runway.cfngin.lookups.handlers.ssmstore.get_session",
        return_value=SessionStub(client),
    )
    def test_ssmstore_handler(self, _mock_client):
        """Test ssmstore handler."""
        self.stubber.add_response(
            "get_parameters", self.get_parameters_response, self.expected_params
        )
        with self.stubber:
            value = SsmstoreLookup.handle(self.ssmkey)
            self.assertEqual(value, self.ssmvalue)
            self.assertIsInstance(value, string_types)

    @mock.patch(
        "runway.cfngin.lookups.handlers.ssmstore.get_session",
        return_value=SessionStub(client),
    )
    def test_ssmstore_invalid_value_handler(self, _mock_client):
        """Test ssmstore invalid value handler."""
        self.stubber.add_response(
            "get_parameters", self.invalid_get_parameters_response, self.expected_params
        )
        with self.stubber:
            try:
                SsmstoreLookup.handle(self.ssmkey)
            except ValueError:
                assert True

    @mock.patch(
        "runway.cfngin.lookups.handlers.ssmstore.get_session",
        return_value=SessionStub(client),
    )
    def test_ssmstore_handler_with_region(self, _mock_client):
        """Test ssmstore handler with region."""
        self.stubber.add_response(
            "get_parameters", self.get_parameters_response, self.expected_params
        )
        with self.stubber:
            region = "us-east-1"
            temp_value = "%s@%s" % (region, self.ssmkey)
            value = SsmstoreLookup.handle(temp_value)
            self.assertEqual(value, self.ssmvalue)
