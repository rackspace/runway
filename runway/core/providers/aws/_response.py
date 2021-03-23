"""Base class for AWS responses."""
# pylint: disable=invalid-name
from http import HTTPStatus
from typing import Any, Dict, Optional


class ResponseError:
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        code: A unique short code representing the error that was emitted.
        message: A longer human readable error message.

    """

    def __init__(self, *, Code: str = "", Message: str = "") -> None:  # noqa
        """Instantiate class.

        Args:
            Code: A unique short code representing the error that was emitted.
            Message: A longer human readable error message.

        """
        self.code = Code
        self.message = Message

    def __bool__(self) -> bool:
        """Implement evaluation of instances as a bool."""
        return bool(self.code or self.message)


class ResponseMetadata:
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        host_id: Host ID data.
        https_headers: A map of response header keys and
            their respective values.
        http_status_code: The HTTP status code of the response (e.g., 200, 404).
        request_id: The unique request ID associated with the response.
            Log this value when debugging requests for AWS support.
        retry_attempts: The number of retries that were attempted
            before the request was completed.

    """

    def __init__(
        self,
        *,
        HostId: Optional[str] = None,  # noqa
        HTTPHeaders: Optional[Dict[str, Any]] = None,  # noqa
        HTTPStatusCode: int = 200,  # noqa
        RequestId: Optional[str] = None,  # noqa
        RetryAttempts: int = 0,  # noqa
    ) -> None:
        """Instantiate class.

        Keyword Args:
            HostId: Host ID data.
            HTTPHeaders: A map of response header keys and their respective values.
            HTTPStatusCode: The HTTP status code of the response (e.g., 200, 404).
            RequestId: The unique request ID associated with the response.
                Log this value when debugging requests for AWS support.
            RetryAttempts: The number of retries that were attempted before the
                request was completed.

        """
        self.host_id = HostId
        self.https_headers = HTTPHeaders or {}
        self.http_status_code = HTTPStatusCode
        self.request_id = RequestId
        self.retry_attempts = RetryAttempts

    @property
    def forbidden(self) -> bool:
        """Whether the response returned 403 (forbidden)."""
        return self.http_status_code == HTTPStatus.FORBIDDEN

    @property
    def not_found(self) -> bool:
        """Whether the response returned 404 (Not Found)."""
        return self.http_status_code == HTTPStatus.NOT_FOUND


class BaseResponse:
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        error: Information about a service or networking error.
        metadata: Information about the request.

    """

    def __init__(self, **kwargs: Any) -> None:
        """Instantiate class.

        Keyword Args:
            Error: Information about a service or networking error.
            ResponseMetadata: Information about the request.

        """
        self.error = ResponseError(**kwargs.pop("Error", {}))  # type: ignore
        self.metadata = ResponseMetadata(**kwargs.pop("ResponseMetadata", {}))  # type: ignore
