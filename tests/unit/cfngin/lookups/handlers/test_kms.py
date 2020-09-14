"""Tests for runway.cfngin.lookups.handlers.kms."""
import codecs
import sys
import unittest

import boto3
from botocore.stub import Stubber
from mock import patch

from runway.cfngin.lookups.handlers.kms import KmsLookup

from ...factories import SessionStub, mock_provider

REGION = "us-east-1"


class TestKMSHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.kms.KmsLookup."""

    client = boto3.client(
        "kms",
        region_name=REGION,
        # bypass the need to have these in the env
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )

    def setUp(self):
        """Run before tests."""
        self.stubber = Stubber(self.client)
        self.provider = mock_provider(region=REGION)
        self.secret = "my secret"

    @patch(
        "runway.cfngin.lookups.handlers.kms.get_session",
        return_value=SessionStub(client),
    )
    def test_kms_handler(self, _mock_client):
        """Test kms handler."""
        self.stubber.add_response(
            "decrypt",
            # TODO: drop ternary when dropping python 2 support
            {
                "Plaintext": self.secret.encode()
                if sys.version_info[0] > 2
                else self.secret
            },
            {"CiphertextBlob": codecs.decode(self.secret.encode(), "base64")},
        )

        with self.stubber:
            self.assertEqual(
                self.secret,
                KmsLookup.handle(value=self.secret, provider=self.provider),
            )
            self.stubber.assert_no_pending_responses()

    @patch(
        "runway.cfngin.lookups.handlers.kms.get_session",
        return_value=SessionStub(client),
    )
    def test_kms_handler_with_region(self, _mock_client):
        """Test kms handler with region."""
        value = "{}@{}".format(REGION, self.secret)

        self.stubber.add_response(
            "decrypt",
            # TODO: drop ternary when dropping python 2 support
            {
                "Plaintext": self.secret.encode()
                if sys.version_info[0] > 2
                else self.secret
            },
            {"CiphertextBlob": codecs.decode(self.secret.encode(), "base64")},
        )

        with self.stubber:
            self.assertEqual(
                self.secret, KmsLookup.handle(value=value, provider=self.provider)
            )
            self.stubber.assert_no_pending_responses()
