"""Test runway.lookups.handlers.ecr."""
# pylint: disable=no-self-use,too-few-public-methods,redefined-outer-name
import base64
import datetime
from typing import TYPE_CHECKING

import pytest

from runway.lookups.handlers.ecr import EcrLookup

if TYPE_CHECKING:
    from mock import MagicMock
    from pytest_mock import MockerFixture

    from ...factories import MockCFNginContext, MockRunwayContext

MODULE = "runway.lookups.handlers.ecr"


@pytest.fixture(scope="function")
def mock_format_results(mocker):  # type: ("MockerFixture") -> "MagicMock"
    """Mock EcrLookup.format_results."""
    return mocker.patch.object(
        EcrLookup, "format_results", return_value="EcrLookup.format_results()"
    )


class TestEcrLookup(object):
    """Test runway.lookups.handlers.ecr.EcrLookup."""

    def test_get_login_password(
        self,
        cfngin_context,  # type: "MockCFNginContext"
        runway_context,  # type: "MockRunwayContext"
    ):  # type: (...) -> None
        """Test get_login_password."""
        cfngin_stubber = cfngin_context.add_stubber("ecr")
        runway_stubber = runway_context.add_stubber("ecr")

        password = "p@ssword"
        response = {
            "authorizationData": [
                {
                    "authorizationToken": base64.b64encode(
                        ("AWS:" + password).encode()
                    ).decode(),
                    "expiresAt": datetime.datetime(2015, 1, 1),
                    "proxyEndpoint": "string",
                }
            ]
        }

        cfngin_stubber.add_response("get_authorization_token", response, {})
        runway_stubber.add_response("get_authorization_token", response, {})

        with cfngin_stubber, runway_stubber:
            assert (
                EcrLookup.get_login_password(cfngin_context.get_session().client("ecr"))
                == password
            )
            assert (
                EcrLookup.get_login_password(runway_context.get_session().client("ecr"))
                == password
            )
        cfngin_stubber.assert_no_pending_responses()
        runway_stubber.assert_no_pending_responses()

    def test_handle_login_password(self, mock_format_results, mocker, runway_context):
        # type: ("MagicMock", "MockerFixture", "MockRunwayContext") -> None
        """Test handle login-password."""
        runway_context.add_stubber("ecr")
        mock_get_login_password = mocker.patch.object(
            EcrLookup,
            "get_login_password",
            return_value="EcrLookup.get_login_password()",
        )
        assert (
            EcrLookup.handle("login-password", runway_context)
            == mock_format_results.return_value
        )
        mock_get_login_password.assert_called_once()
        mock_format_results.assert_called_once_with(
            mock_get_login_password.return_value
        )

    def test_handle_value_error(self, runway_context):
        # type: ("MockRunwayContext") -> None
        """Test handle raise ValueError."""
        runway_context.add_stubber("ecr")
        with pytest.raises(ValueError) as excinfo:
            EcrLookup.handle("unsupported", runway_context)
        assert str(excinfo.value) == "ecr lookup does not support 'unsupported'"
        with pytest.raises(ValueError):
            EcrLookup.handle("unsupported::default=something", runway_context)
