"""Sign user out of Cognito and remove all Cookie Headers."""

import logging
from urllib.parse import urlencode  # pylint: disable=no-name-in-module,import-error

from shared import (  # noqa pylint: disable=import-error
    extract_and_parse_cookies,
    get_config,
    get_cookie_headers,
)

LOGGER = logging.getLogger(__name__)
CONFIG = get_config()


def handler(event, _context):
    """Handle the signout event."""
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    extracted = extract_and_parse_cookies(request["headers"], CONFIG.get("client_id"))

    if not extracted.get("idToken"):
        return {
            "body": "Bad Request",
            "status": "400",
            "statusDescription": "Bad Request",
            "headers": CONFIG.get("cloud_front_headers"),
        }

    tokens = {
        "id_token": extracted.get("idToken"),
        "access_token": extracted.get("accessToken"),
        "refresh_token": extracted.get("refreshToken"),
    }
    query_string = {
        "logout_uri": "https://%s%s"
        % (domain_name, CONFIG.get("redirect_path_sign_out")),
        "client_id": CONFIG.get("client_id"),
    }

    headers = {
        # Redirect the user to logout
        "location": [
            {
                "key": "location",
                "value": "https://%s/logout?%s"
                % (CONFIG.get("cognito_auth_domain"), urlencode(query_string)),
            }
        ],
        "set-cookie": get_cookie_headers(
            CONFIG.get("client_id"),
            CONFIG.get("oauth_scopes"),
            tokens,
            domain_name,
            CONFIG.get("cookie_settings"),
            # Make sure we expire all the tokens during retrieval
            expire_all_tokens=True,
        ),
    }
    headers.update(CONFIG.get("cloud_front_headers"))

    return {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": headers,
    }
