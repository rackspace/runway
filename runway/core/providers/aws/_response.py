"""Base class for AWS responses."""
from typing import Any, Dict, Union  # pylint: disable=W

from ....http_backport import HTTPStatus


class ResponseError(object):  # pylint: disable=too-few-public-methods
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        code (str): A unique short code representing the error that was emitted.
        message (str): A longer human readable error message.

    """

    def __init__(self, **kwargs):
        # type: (str) -> None
        """Instantiate class.

        Keyword Args:
            Code (str): A unique short code representing the error that was emitted.
            Message (str): A longer human readable error message.

        """
        self.code = kwargs.get("Code", "")
        self.message = kwargs.get("Message", "")

    def __bool__(self):
        # type: () -> bool
        """Implement evaluation of instances as a bool."""
        return bool(self.code or self.message)

    __nonzero__ = __bool__  # python2 compatability


class ResponseMetadata(object):
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        host_id (Optional[str]): Host ID data.
        https_headers (Dict[str, Any]): A map of response header keys and
            their respective values.
        http_status_code (int): The HTTP status code of the response (e.g., 200, 404).
        request_id (Optional[str]): The unique request ID associated with the response.
            Log this value when debugging requests for AWS support.
        retry_attempts (int): The number of retries that were attempted
            before the request was completed.

    """

    def __init__(self, **kwargs):
        # type: (Union[int, None, str]) -> None
        """Instantiate class.

        Keyword Args:
            HostId (str): Host ID data.
            HTTPHeaders (Dict[str, Any]): A map of response header keys and
                their respective values.
            HTTPStatusCode (int): The HTTP status code of the response
                (e.g., 200, 404).
            RequestId (str): The unique request ID associated with the response.
                Log this value when debugging requests for AWS support.
            RetryAttempts (int): The number of retries that were attempted
                before the request was completed.

        """
        self.host_id = kwargs.get("HostId")
        self.https_headers = kwargs.get("HTTPHeaders", {})
        self.http_status_code = kwargs.get("HTTPStatusCode", 200)
        self.request_id = kwargs.get("RequestId")
        self.retry_attempts = kwargs.get("RetryAttempts", 0)

    @property
    def forbidden(self):
        # type: () -> bool
        """Whether the response returned 403 (forbidden)."""
        return self.http_status_code == HTTPStatus.FORBIDDEN

    @property
    def not_found(self):
        # type: () -> bool
        """Whether the response returned 404 (Not Found)."""
        return self.http_status_code == HTTPStatus.NOT_FOUND


class BaseResponse(object):  # pylint: disable=too-few-public-methods
    """Analyse the response from AWS S3 HeadBucket API response.

    Attributes:
        error (ResponseError): Information about a service or networking error.
        metadata (ResponseMetadata): Information about the request.

    """

    def __init__(self, **kwargs):
        # type: (Dict[str, Any]) -> None
        """Instantiate class.

        Keyword Args:
            Error: Information about a service or networking error.
            ResponseMetadata: Information about the request.

        """
        self.error = ResponseError(**kwargs.pop("Error", {}))
        self.metadata = ResponseMetadata(**kwargs.pop("ResponseMetadata", {}))
