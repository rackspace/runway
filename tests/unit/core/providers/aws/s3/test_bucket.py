"""Test runway.core.providers.aws.s3._bucket."""

# pyright: basic
from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from runway.core.providers.aws import BaseResponse
from runway.core.providers.aws.s3 import Bucket

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from .....factories import MockRunwayContext

MODULE = "runway.core.providers.aws.s3._bucket"


class TestBucket:
    """Test runway.core.providers.aws.s3._bucket.Bucket."""

    @pytest.mark.parametrize(
        "forbidden, not_found, expected",
        [
            (False, False, True),
            (False, True, False),
            (True, False, False),
        ],
    )
    def test___bool__(
        self,
        expected: bool,
        forbidden: bool,
        mocker: MockerFixture,
        not_found: bool,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __bool__."""
        response = BaseResponse()
        if forbidden:
            response.metadata.http_status_code = HTTPStatus.FORBIDDEN
        elif not_found:
            response.metadata.http_status_code = HTTPStatus.NOT_FOUND
        mocker.patch.object(Bucket, "head", response)
        assert Bucket(runway_context, "test-bucket").exists is expected

    def test_client(self) -> None:
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

    def test_create(self, runway_context: MockRunwayContext) -> None:
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

    def test_create_exists(
        self, caplog: pytest.LogCaptureFixture, runway_context: MockRunwayContext
    ) -> None:
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

    def test_create_forbidden(
        self, caplog: pytest.LogCaptureFixture, runway_context: MockRunwayContext
    ) -> None:
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

    def test_create_us_west_2(self, runway_context: MockRunwayContext) -> None:
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

    def test_enable_versioning(self, runway_context: MockRunwayContext) -> None:
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

    def test_enable_versioning_skipped(
        self, caplog: pytest.LogCaptureFixture, runway_context: MockRunwayContext
    ) -> None:
        """Test enable_versioning with Status=Enabled."""
        caplog.set_level(logging.DEBUG, logger="runway.core.providers.aws.s3.bucket")
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        stubber.add_response(
            "get_bucket_versioning", {"Status": "Enabled"}, {"Bucket": "test-bucket"}
        )

        with stubber:
            bucket.enable_versioning()
        stubber.assert_no_pending_responses()
        assert (
            'did not modify versioning policy for bucket "test-bucket"; already enabled'
        ) in caplog.messages

    @pytest.mark.parametrize(
        "forbidden, not_found, expected",
        [
            (False, False, True),
            (False, True, False),
            (True, False, False),
        ],
    )
    def test_exists(
        self,
        expected: bool,
        forbidden: bool,
        mocker: MockerFixture,
        not_found: bool,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test not_found."""
        response = BaseResponse()
        if forbidden:
            response.metadata.http_status_code = HTTPStatus.FORBIDDEN
        elif not_found:
            response.metadata.http_status_code = HTTPStatus.NOT_FOUND
        mocker.patch.object(Bucket, "head", response)
        assert Bucket(runway_context, "test-bucket").exists is expected

    @pytest.mark.parametrize("forbidden, expected", [(True, True), (False, False)])
    def test_forbidden(
        self,
        expected: bool,
        forbidden: bool,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test forbidden."""
        response = BaseResponse()
        response.metadata.http_status_code = HTTPStatus.FORBIDDEN if forbidden else HTTPStatus.OK
        mocker.patch.object(Bucket, "head", response)
        assert Bucket(runway_context, "test-bucket").forbidden is expected

    def test_format_bucket_path_uri(self) -> None:
        """Test format_bucket_path_uri."""
        uri = "s3://test-bucket"
        bucket = Bucket(MagicMock(), uri[5:])
        assert bucket.format_bucket_path_uri() == uri
        assert bucket.format_bucket_path_uri(key="test.txt") == f"{uri}/test.txt"
        assert (
            bucket.format_bucket_path_uri(key="test.txt", prefix="prefix")
            == f"{uri}/prefix/test.txt"
        )
        assert bucket.format_bucket_path_uri(prefix="prefix") == f"{uri}/prefix"

    def test_get_versioning(self, runway_context: MockRunwayContext) -> None:
        """Test get_versioning."""
        stubber = runway_context.add_stubber("s3")
        bucket = Bucket(runway_context, "test-bucket")

        response = {"Status": "Enabled", "MFADelete": "Enabled"}

        stubber.add_response("get_bucket_versioning", response, {"Bucket": "test-bucket"})

        with stubber:
            assert bucket.get_versioning() == response
        stubber.assert_no_pending_responses()

    def test_head(self, runway_context: MockRunwayContext) -> None:
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

    def test_head_clienterror(
        self, caplog: pytest.LogCaptureFixture, runway_context: MockRunwayContext
    ) -> None:
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

    @pytest.mark.parametrize("not_found, expected", [(True, True), (False, False)])
    def test_not_found(
        self,
        expected: bool,
        mocker: MockerFixture,
        not_found: bool,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test not_found."""
        response = BaseResponse()
        response.metadata.http_status_code = HTTPStatus.NOT_FOUND if not_found else HTTPStatus.OK
        mocker.patch.object(Bucket, "head", response)
        assert Bucket(runway_context, "test-bucket").not_found is expected

    def test_sync_from_local(
        self, mocker: MockerFixture, runway_context: MockRunwayContext
    ) -> None:
        """Test sync_from_local."""
        mock_handler = MagicMock()
        mock_handler_class = mocker.patch(f"{MODULE}.S3SyncHandler", return_value=mock_handler)
        runway_context.add_stubber("s3")
        src_directory = "/test/"
        obj = Bucket(runway_context, "test-bucket")
        assert not obj.sync_from_local(
            src_directory, delete=True, exclude=["something"], prefix="prefix"
        )
        mock_handler_class.assert_called_once_with(
            context=runway_context,
            delete=True,
            dest="s3://test-bucket/prefix",
            exclude=["something"],
            follow_symlinks=False,
            include=None,
            session=obj.session,
            src=src_directory,
        )
        mock_handler.run.assert_called_once_with()

    def test_sync_to_local(self, mocker: MockerFixture, runway_context: MockRunwayContext) -> None:
        """Test sync_to_local."""
        mock_handler = MagicMock()
        mock_handler_class = mocker.patch(f"{MODULE}.S3SyncHandler", return_value=mock_handler)
        runway_context.add_stubber("s3")
        dest_directory = "/test/"
        obj = Bucket(runway_context, "test-bucket")
        assert not obj.sync_to_local(dest_directory, follow_symlinks=True, include=["something"])
        mock_handler_class.assert_called_once_with(
            context=runway_context,
            delete=False,
            dest=dest_directory,
            exclude=None,
            follow_symlinks=True,
            include=["something"],
            session=obj.session,
            src="s3://test-bucket",
        )
        mock_handler.run.assert_called_once_with()
