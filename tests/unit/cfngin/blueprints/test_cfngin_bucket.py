"""Test runway.cfngin.blueprints.cfngin_bucket."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock

from troposphere import s3

from runway import __version__
from runway.cfngin.blueprints.base import CFNParameter
from runway.cfngin.blueprints.cfngin_bucket import CfnginBucket

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext

MODULE = "runway.cfngin.blueprints.cfngin_bucket"


class TestCfnginBucket:
    """Test CfnginBucket."""

    def test_bucket(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test bucket."""
        mocker.patch.object(
            CfnginBucket,
            "variables",
            {
                "AccessControl": Mock(ref="Ref(AccessControl)"),
                "VersioningStatus": Mock(ref="Ref(VersioningStatus)"),
            },
        )
        mock_bucket = Mock(get_att=Mock(return_value="get_att"), ref=Mock(return_value="ref"))
        mock_bucket.return_value = mock_bucket
        mocker.patch(f"{MODULE}.s3", Bucket=mock_bucket)
        bucket_encryption = mocker.patch.object(
            CfnginBucket,
            "bucket_encryption",
            "bucket_encryption",
        )
        bucket_name = mocker.patch.object(
            CfnginBucket,
            "bucket_name",
            "bucket_name",
        )
        bucket_tags = mocker.patch.object(
            CfnginBucket,
            "bucket_tags",
            "bucket_tags",
        )
        obj = CfnginBucket("test", cfngin_context)
        assert obj.bucket == mock_bucket
        mock_bucket.assert_called_once_with(
            "Bucket",
            AccessControl="Ref(AccessControl)",
            BucketEncryption=bucket_encryption,
            BucketName=bucket_name,
            OwnershipControls=ANY,  # troposphere objects can't be compared atm
            Tags=bucket_tags,
            VersioningConfiguration=ANY,  # troposphere objects can't be compared atm
        )
        assert "BucketArn" in obj.template.outputs
        assert "BucketDomainName" in obj.template.outputs
        assert "BucketName" in obj.template.outputs
        assert "BucketRegionalDomainName" in obj.template.outputs

    def test_bucket_encryption(self, cfngin_context: CfnginContext) -> None:
        """Test bucket_encryption."""
        obj = CfnginBucket("test", cfngin_context)
        assert isinstance(obj.bucket_encryption, s3.BucketEncryption)
        assert len(obj.bucket_encryption.ServerSideEncryptionConfiguration) == 1
        assert (
            obj.bucket_encryption.ServerSideEncryptionConfiguration[
                0
            ].ServerSideEncryptionByDefault.SSEAlgorithm
            == "AES256"
        )

    def test_bucket_name(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test bucket_name."""
        mocker.patch.object(
            CfnginBucket,
            "variables",
            {"BucketName": CFNParameter("BucketName", "something")},
        )
        obj = CfnginBucket("test", cfngin_context)
        assert obj.bucket_name.to_dict() == {
            "Fn::If": [
                "BucketNameProvided",
                {"Ref": "BucketName"},
                {"Ref": "AWS::NoValue"},
            ]
        }
        assert len(obj.template.conditions) == 1
        assert obj.template.conditions["BucketNameProvided"].to_dict() == {
            "Fn::Or": [
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "BucketName"}, ""]}]},
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "BucketName"}, "undefined"]}]},
            ]
        }

    def test_bucket_tags(self, cfngin_context: CfnginContext) -> None:
        """Test bucket_tags."""
        obj = CfnginBucket("test", cfngin_context)
        assert obj.bucket_tags.to_dict() == [{"Key": "version", "Value": __version__}]

    def test_create_template(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test create_template."""
        bucket = mocker.patch.object(CfnginBucket, "bucket", "bucket")
        obj = CfnginBucket("test", cfngin_context)
        mock_template = mocker.patch.object(obj, "template")
        assert not obj.create_template()
        mock_template.set_description.assert_called_once_with(obj.DESCRIPTION)
        mock_template.set_version.assert_called_once_with("2010-09-09")
        mock_template.add_resource.assert_called_once_with(bucket)
