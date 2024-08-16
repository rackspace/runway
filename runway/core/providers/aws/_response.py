"""Base class for AWS responses."""

from http import HTTPStatus
from typing import Any

from pydantic import Field

from ....utils import BaseModel


class ResponseError(BaseModel):
    """Analyse the response from AWS S3 HeadBucket API response.

    Keyword Args:
        Code: A unique short code representing the error that was emitted.
        Message: A longer human readable error message.

    """

    code: str = Field(default="", alias="Code")
    """A unique short code representing the error that was emitted."""

    message: str = Field(default="", alias="Message")
    """A longer human readable error message."""

    def __bool__(self) -> bool:
        """Implement evaluation of instances as a bool."""
        return bool(self.code or self.message)


class ResponseMetadata(BaseModel):
    """Analyse the response from AWS S3 HeadBucket API response.

    Keyword Args:
        HostId: Host ID data.
        HTTPHeaders: A map of response header keys and their respective values.
        HTTPStatusCode: The HTTP status code of the response (e.g., 200, 404).
        RequestId: The unique request ID associated with the response.
            Log this value when debugging requests for AWS support.
        RetryAttempts: The number of retries that were attempted before the
            request was completed.

    """

    host_id: str = Field(default="", alias="HostId")
    """Host ID data."""

    https_headers: dict[str, Any] = Field(default={}, alias="HTTPHeaders")
    """A map of response header keys and their respective values."""

    http_status_code: int = Field(default=200, alias="HTTPStatusCode")
    """he HTTP status code of the response (e.g., 200, 404)."""

    request_id: str = Field(default="", alias="RequestId")
    """The unique request ID associated with the response.
    Log this value when debugging requests for AWS support.

    """

    retry_attempts: int = Field(default=0, alias="RetryAttempts")
    """The number of retries that were attempted before the request was completed."""

    @property
    def forbidden(self) -> bool:
        """Whether the response returned 403 (forbidden)."""
        return self.http_status_code == HTTPStatus.FORBIDDEN

    @property
    def not_found(self) -> bool:
        """Whether the response returned 404 (Not Found)."""
        return self.http_status_code == HTTPStatus.NOT_FOUND


class BaseResponse(BaseModel):
    """Analyse the response from AWS S3 HeadBucket API response.

    Keyword Args:
        Error: Information about a service or networking error.
        ResponseMetadata: Information about the request.

    """

    error: ResponseError = Field(default=ResponseError(), alias="Error")
    """Information about a service or networking error."""

    metadata: ResponseMetadata = Field(default=ResponseMetadata(), alias="ResponseMetadata")
    """Information about the request."""
