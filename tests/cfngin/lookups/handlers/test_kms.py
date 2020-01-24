"""Tests for runway.cfngin.lookups.handlers.kms."""
import codecs
import unittest

import boto3
from botocore.stub import Stubber
from mock import patch

from runway.cfngin.lookups.handlers.kms import KmsLookup

from ...factories import SessionStub, mock_provider

REGION = 'us-east-1'


class TestKMSHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.kms.KmsLookup."""

    client = boto3.client('kms', region_name=REGION,
                          # bypass the need to have these in the env
                          aws_access_key_id='testing',
                          aws_secret_access_key='testing')

    def setUp(self):
        """Run before tests."""
        self.stubber = Stubber(self.client)
        self.provider = mock_provider(region=REGION)
        self.secret = b'my secret'

    @patch("runway.cfngin.lookups.handlers.kms.get_session",
           return_value=SessionStub(client))
    def test_kms_handler(self, _mock_client):
        """Test kms handler."""
        self.stubber.add_response('decrypt', {'Plaintext': self.secret},
                                  {'CiphertextBlob': codecs.decode(self.secret,
                                                                   'base64')})

        with self.stubber:
            self.assertEqual(self.secret,
                             KmsLookup.handle(value=self.secret.decode(),
                                              provider=self.provider))
            self.stubber.assert_no_pending_responses()

    @patch("runway.cfngin.lookups.handlers.kms.get_session",
           return_value=SessionStub(client))
    def test_kms_handler_with_region(self, _mock_client):
        """Test kms handler with region."""
        value = '{}@{}'.format(REGION, self.secret.decode())

        self.stubber.add_response('decrypt', {'Plaintext': self.secret},
                                  {'CiphertextBlob': codecs.decode(self.secret,
                                                                   'base64')})

        with self.stubber:
            self.assertEqual(self.secret,
                             KmsLookup.handle(value=value,
                                              provider=self.provider))
            self.stubber.assert_no_pending_responses()
