"""Test runway.core.providers.aws.s3._bucket."""
# pylint: disable=no-self-use
import logging

from mock import MagicMock

from runway.core.providers.aws import BaseResponse
from runway.core.providers.aws.s3 import Bucket
from runway.http_backport import HTTPStatus

MODULE = "runway.core.providers.aws.s3._bucket"


class TestBucket(object):
    """Test runway.core.providers.aws.s3._bucket.Bucket."""

    def test_client(self):
        """Test client."""
        mock_ctx = MagicMock()
        mock_session = MagicMock()
        mock_client = MagicMock()

        mock_ctx.get_session.return_value = mock_session
        mock_session.client.return_value = mock_client

        bucket = Bucket(mock_ctx, "test-bucket", region="us-west-2")
        assert bucket.client == mock_client
        mock_ctx.get_session.assert_called_once_with(region="us-west-2")
        mock_session.client.assert_called_once_with("s3")

    def test_create(self, runway_context):
        """Test create."""
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_client_error(
            "head_bucket",
            "NoSuchBucket",
            "Not Found",
            404,
            expected_params={"Bucket": "test-bucket"},
        )
        stubber.add_response(
            "create_bucket",
            {"Location": "us-east-1"},
            {"ACL": "private", "Bucket": "test-bucket"},
        )

        with stubber:
            assert bucket.create(ACL="private")
        stubber.assert_no_pending_responses()

    def test_create_exists(self, caplog, runway_context):
        """Test create with exists=True."""
        caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.s3.bucket")
        stubber = runway_context.add_stubber("s3", region="us-west-2")
        bucket = Bucket(runway_context, "test-bucket", region="us-west-2")

        stubber.add_response(
            "head_bucket",
            {"ResponseMetadata": {"HostId": "test", "HTTPStatusCode": 200}},
            {"Bucket": "test-bucket"},
        )

        with stubber:
            assert not bucket.create()
        stubber.assert_no_pending_responses()
        assert "bucket already exists" in "\n".join(caplog.messages)

    def test_create_forbidden(self, caplog, runway_context):
        """Test create with forbidden=True."""
        caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.s3.bucket")
        stubber = runway_context.add_stubber("s3", region="us-west-2")
        bucket = Bucket(runway_context, "test-bucket", region="us-west-2")

        stubber.add_client_error(
            "head_bucket",
            "AccessDenied",
            "Forbidden",
            403,
            expected_params={"Bucket": "test-bucket"},
        )

        with stubber:
            assert not bucket.create()
        stubber.assert_no_pending_responses()
        assert "access denied" in "\n".join(caplog.messages)

    def test_create_us_west_2(self, runway_context):
        """Test create with region=us-west-2."""
        stubber = runway_context.add_stubber("s3", region="us-west-2")
        bucket = Bucket(runway_context, "test-bucket", region="us-west-2")

        stubber.add_client_error(
            "head_bucket",
            "NoSuchBucket",
            "The specified bucket does not exist.",
            404,
            expected_params={"Bucket": "test-bucket"},
        )
        stubber.add_response(
            "create_bucket",
            {"Location": "us-east-1"},
            {
                "Bucket": "test-bucket",
                "CreateBucketConfiguration": {"LocationConstraint": "us-west-2"},
            },
        )

        with stubber:
            assert bucket.create()
        stubber.assert_no_pending_responses()

    def test_enable_versioning(self, runway_context):
        """Test enable_versioning."""
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_response(
            "get_bucket_versioning",
            {"Status": "Suspended", "MFADelete": "Enabled"},
            {"Bucket": "test-bucket"},
        )
        stubber.add_response(
            "put_bucket_versioning",
            {},
            {
                "Bucket": "test-bucket",
                "VersioningConfiguration": {
                    "Status": "Enabled",
                    "MFADelete": "Enabled",
                },
            },
        )

        with stubber:
            bucket.enable_versioning()
        stubber.assert_no_pending_responses()

    def test_enable_versioning_skipped(self, caplog, runway_context):
        """Test enable_versioning with Status=Enabled."""
        caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.s3.bucket")
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_response(
            "get_bucket_versioning", {"Status": "Enabled"}, {"Bucket": "test-bucket"},
        )

        with stubber:
            bucket.enable_versioning()
        stubber.assert_no_pending_responses()
        assert (
            'did not modify versioning policy for bucket "test-bucket"; already enabled'
        ) in caplog.messages

    def test_exists(self, monkeypatch, runway_context):
        """Test not_found."""
        mock_head = MagicMock(spec=BaseResponse())
        monkeypatch.setattr(Bucket, "head", mock_head)
        bucket = Bucket(runway_context, "test-bucket")

        mock_head.metadata.not_found = True
        assert not bucket.exists  # initial value

        mock_head.metadata.not_found = False
        assert not bucket.exists  # cached value
        del bucket.not_found

        assert bucket.exists  # updated value

    def test_forbidden(self, monkeypatch, runway_context):
        """Test forbidden."""
        mock_head = MagicMock(spec=BaseResponse())
        monkeypatch.setattr(Bucket, "head", mock_head)
        bucket = Bucket(runway_context, "test-bucket")

        mock_head.metadata.forbidden = True
        assert bucket.forbidden  # initial value

        mock_head.metadata.forbidden = False
        assert bucket.forbidden  # cached value
        del bucket.forbidden

        assert not bucket.forbidden  # updated value

    def test_get_versioning(self, runway_context):
        """Test get_versioning."""
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        response = {"Status": "Enabled", "MFADelete": "Enabled"}

        stubber.add_response(
            "get_bucket_versioning", response, {"Bucket": "test-bucket"}
        )

        with stubber:
            assert bucket.get_versioning() == response
        stubber.assert_no_pending_responses()

    def test_head(self, runway_context):
        """Test head."""
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_response(
            "head_bucket",
            {"ResponseMetadata": {"HostId": "test", "HTTPStatusCode": 200}},
            {"Bucket": "test-bucket"},
        )

        with stubber:
            assert bucket.head.metadata.host_id == "test"
            assert bucket.head.metadata.http_status_code == HTTPStatus.OK
        stubber.assert_no_pending_responses()

    def test_head_clienterror(self, caplog, runway_context):
        """Test head with ClientError."""
        caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.s3.bucket")
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_client_error(
            "head_bucket",
            "AccessDenied",
            "Forbidden",
            403,
            expected_params={"Bucket": "test-bucket"},
        )

        with stubber:
            assert bucket.head.metadata.http_status_code == HTTPStatus.FORBIDDEN
        stubber.assert_no_pending_responses()
        assert "received an error from AWS S3" in "\n".join(caplog.messages)

    def test_not_found(self, monkeypatch, runway_context):
        """Test not_found."""
        mock_head = MagicMock(spec=BaseResponse())
        monkeypatch.setattr(Bucket, "head", mock_head)
        bucket = Bucket(runway_context, "test-bucket")

        mock_head.metadata.not_found = True
        assert bucket.not_found  # initial value

        mock_head.metadata.not_found = False
        assert bucket.not_found  # cached value
        del bucket.not_found

        assert not bucket.not_found  # updated value
