"""Test runway.core.providers.aws._response."""

# pyright: basic
from __future__ import annotations

from runway.core.providers.aws import BaseResponse, ResponseError, ResponseMetadata

MODULE = "runway.core.providers.aws._response"


class TestBaseResponse:
    """Test runway.core.providers.aws._response.BaseResponse."""

    def test_init(self) -> None:
        """Test init and the attributes it sets."""
        data = {"Error": {"Code": "something"}, "ResponseMetadata": {"HostId": "id"}}
        response = BaseResponse(**data.copy())

        assert isinstance(response.error, ResponseError)
        assert response.error.code == data["Error"]["Code"]
        assert isinstance(response.metadata, ResponseMetadata)
        assert response.metadata.host_id == data["ResponseMetadata"]["HostId"]

    def test_init_default(self) -> None:
        """Test init default values and the attributes it sets."""
        response = BaseResponse()
        assert response.error == ResponseError()
        assert response.metadata == ResponseMetadata()


class TestResponseError:
    """Test runway.core.providers.aws._response.ResponseError."""

    def test_init(self) -> None:
        """Test init and the attributes it sets."""
        data = {"Code": "error_code", "Message": "error_message"}
        error = ResponseError(**data.copy())
        assert error
        assert error.code == data["Code"]
        assert error.message == data["Message"]

    def test_init_defaults(self) -> None:
        """Test init default values and the attributes it sets."""
        error = ResponseError()
        assert not error
        assert error.code == ""
        assert error.message == ""


class TestResponseMetadata:
    """Test runway.core.providers.aws._response.ResponseMetadata."""

    def test_forbidden(self) -> None:
        """Test forbidden."""
        assert ResponseMetadata(HTTPStatusCode=403).forbidden
        assert not ResponseMetadata(HTTPStatusCode=404).forbidden

    def test_init(self) -> None:
        """Test init and the attributes it sets."""
        data = {
            "HostId": "host_id",
            "HTTPHeaders": {"header00": "header00_val"},
            "HTTPStatusCode": 100,
            "RequestId": "request_id",
            "RetryAttempts": 5,
        }
        metadata = ResponseMetadata(**data.copy())

        assert metadata.host_id == data["HostId"]
        assert metadata.https_headers == data["HTTPHeaders"]
        assert metadata.http_status_code == data["HTTPStatusCode"]
        assert metadata.request_id == data["RequestId"]
        assert metadata.retry_attempts == data["RetryAttempts"]

    def test_init_defaults(self) -> None:
        """Test init default values and the attributes it sets."""
        metadata = ResponseMetadata()

        assert not metadata.host_id
        assert metadata.https_headers == {}
        assert metadata.http_status_code == 200
        assert not metadata.request_id
        assert metadata.retry_attempts == 0

    def test_not_found(self) -> None:
        """Test not_found."""
        assert not ResponseMetadata(HTTPStatusCode=403).not_found
        assert ResponseMetadata(HTTPStatusCode=404).not_found
