"""Test runway.core.providers.aws._response."""
# pylint: disable=no-self-use
from mock import patch

from runway.core.providers.aws import BaseResponse, ResponseError, ResponseMetadata

MODULE = "runway.core.providers.aws._response"


class TestBaseResponse(object):
    """Test runway.core.providers.aws._response.BaseResponse."""

    @patch(MODULE + ".ResponseMetadata")
    @patch(MODULE + ".ResponseError")
    def test_init(self, mock_error, mock_metadata):
        """Test init and the attributes it sets."""
        data = {"Error": {"Code": "something"}, "ResponseMetadata": {"HostId": "id"}}
        response = BaseResponse(**data.copy())

        assert response.error == mock_error.return_value
        assert response.metadata == mock_metadata.return_value
        mock_error.assert_called_once_with(**data["Error"])
        mock_metadata.assert_called_once_with(**data["ResponseMetadata"])

    @patch(MODULE + ".ResponseMetadata")
    @patch(MODULE + ".ResponseError")
    def test_init_default(self, mock_error, mock_metadata):
        """Test init default values and the attributes it sets."""
        response = BaseResponse()

        assert response.error == mock_error.return_value
        assert response.metadata == mock_metadata.return_value
        mock_error.assert_called_once_with()
        mock_metadata.assert_called_once_with()


class TestResponseError(object):
    """Test runway.core.providers.aws._response.ResponseError."""

    def test_init(self):
        """Test init and the attributes it sets."""
        data = {"Code": "error_code", "Message": "error_message"}
        error = ResponseError(**data.copy())
        assert error
        assert error.code == data["Code"]
        assert error.message == data["Message"]

    def test_init_defaults(self):
        """Test init default values and the attributes it sets."""
        error = ResponseError()
        assert not error
        assert error.code == ""
        assert error.message == ""


class TestResponseMetadata(object):
    """Test runway.core.providers.aws._response.ResponseMetadata."""

    def test_forbidden(self):
        """Test forbidden."""
        assert ResponseMetadata(HTTPStatusCode=403).forbidden
        assert not ResponseMetadata(HTTPStatusCode=404).forbidden

    def test_init(self):
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

    def test_init_defaults(self):
        """Test init default values and the attributes it sets."""
        metadata = ResponseMetadata()

        assert not metadata.host_id
        assert metadata.https_headers == {}
        assert metadata.http_status_code == 200
        assert not metadata.request_id
        assert metadata.retry_attempts == 0

    def test_not_found(self):
        """Test not_found."""
        assert not ResponseMetadata(HTTPStatusCode=403).not_found
        assert ResponseMetadata(HTTPStatusCode=404).not_found
