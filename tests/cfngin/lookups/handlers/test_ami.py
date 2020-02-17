"""Tests for runway.cfngin.lookups.handlers.ami."""
import unittest

import boto3
import mock
from botocore.stub import Stubber

from runway.cfngin.lookups.handlers.ami import AmiLookup, ImageNotFound

from ...factories import SessionStub, mock_provider

REGION = "us-east-1"


class TestAMILookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.ami.ImageNotFound."""

    client = boto3.client("ec2", region_name=REGION,
                          # bypass the need to have these in the env
                          aws_access_key_id='testing',
                          aws_secret_access_key='testing')

    def setUp(self):
        """Run before tests."""
        self.stubber = Stubber(self.client)
        self.provider = mock_provider(region=REGION)

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_single_image(self, _mock_client):
        """Test basic lookup single image."""
        image_id = "ami-fffccc111"
        self.stubber.add_response(
            "describe_images",
            {
                "Images": [
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-13T01:17:44.000Z",
                        "State": "available",
                        "ImageId": image_id,
                        "Name": "Fake Image 1",
                        "VirtualizationType": "hvm",
                    }
                ]
            }
        )

        with self.stubber:
            value = AmiLookup.handle(
                value=r'owners:self name_regex:Fake\sImage\s\d',
                provider=self.provider
            )
            self.assertEqual(value, image_id)

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_with_region(self, _mock_client):
        """Test basic lookup with region."""
        image_id = "ami-fffccc111"
        self.stubber.add_response(
            "describe_images",
            {
                "Images": [
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-13T01:17:44.000Z",
                        "State": "available",
                        "ImageId": image_id,
                        "Name": "Fake Image 1",
                        "VirtualizationType": "hvm",
                    }
                ]
            }
        )

        with self.stubber:
            value = AmiLookup.handle(
                value=r'us-west-1@owners:self name_regex:Fake\sImage\s\d',
                provider=self.provider
            )
            self.assertEqual(value, image_id)

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_multiple_images(self, _mock_client):
        """Test basic lookup multiple images."""
        image_id = "ami-fffccc111"
        self.stubber.add_response(
            "describe_images",
            {
                "Images": [
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-13T01:17:44.000Z",
                        "State": "available",
                        "ImageId": "ami-fffccc110",
                        "Name": "Fake Image 1",
                        "VirtualizationType": "hvm",
                    },
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-14T01:17:44.000Z",
                        "State": "available",
                        "ImageId": image_id,
                        "Name": "Fake Image 2",
                        "VirtualizationType": "hvm",
                    },
                    # include an ARI in the response to ensure it can be handled
                    # (these don't include a 'Name')
                    {
                        'OwnerId': '897883143566',
                        'Architecture': 'x86_64',
                        'CreationDate': '2011-06-24T20:34:25.000Z',
                        'State': 'available',
                        'ImageId': 'ari-e6bc478f',
                        'VirtualizationType': 'paravirtual'
                    }
                ]
            }
        )

        with self.stubber:
            value = AmiLookup.handle(
                value=r'owners:self name_regex:Fake\sImage\s\d',
                provider=self.provider
            )
            self.assertEqual(value, image_id)

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_multiple_images_name_match(self, _mock_client):
        """Test basic lookup multiple images name match."""
        image_id = "ami-fffccc111"
        self.stubber.add_response(
            "describe_images",
            {
                "Images": [
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-13T01:17:44.000Z",
                        "State": "available",
                        "ImageId": "ami-fffccc110",
                        "Name": "Fa---ke Image 1",
                        "VirtualizationType": "hvm",
                    },
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-14T01:17:44.000Z",
                        "State": "available",
                        "ImageId": image_id,
                        "Name": "Fake Image 2",
                        "VirtualizationType": "hvm",
                    },
                ]
            }
        )

        with self.stubber:
            value = AmiLookup.handle(
                value=r'owners:self name_regex:Fake\sImage\s\d',
                provider=self.provider
            )
            self.assertEqual(value, image_id)

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_no_matching_images(self, _mock_client):
        """Test basic lookup no matching images."""
        self.stubber.add_response(
            "describe_images",
            {
                "Images": []
            }
        )

        with self.stubber:
            with self.assertRaises(ImageNotFound):
                AmiLookup.handle(
                    value=r'owners:self name_regex:Fake\sImage\s\d',
                    provider=self.provider
                )

    @mock.patch("runway.cfngin.lookups.handlers.ami.get_session",
                return_value=SessionStub(client))
    def test_basic_lookup_no_matching_images_from_name(self, _mock_client):
        """Test basic lookup no matching images from name."""
        image_id = "ami-fffccc111"
        self.stubber.add_response(
            "describe_images",
            {
                "Images": [
                    {
                        "OwnerId": "897883143566",
                        "Architecture": "x86_64",
                        "CreationDate": "2011-02-13T01:17:44.000Z",
                        "State": "available",
                        "ImageId": image_id,
                        "Name": "Fake Image 1",
                        "VirtualizationType": "hvm",
                    }
                ]
            }
        )

        with self.stubber:
            with self.assertRaises(ImageNotFound):
                AmiLookup.handle(
                    value=r'owners:self name_regex:MyImage\s\d',
                    provider=self.provider
                )
