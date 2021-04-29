"""Sign user out of Cognito and remove all Cookie Headers."""

import logging
from urllib.parse import urlencode

from shared import (  # noqa pylint: disable=import-error
    create_error_html,
    extract_and_parse_cookies,
    generate_cookie_headers,
    get_config,
)

LOGGER = logging.getLogger(__name__)
CONFIG = get_config()


def handler(event, _context):
    """Handle the signout event."""
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    extracted = extract_and_parse_cookies(request["headers"], CONFIG["client_id"])

    if not extracted["id_token"]:
        response = {
            "body": create_error_html(
                "Signed out",
                "You are already signed out",
                "https://%s%s" % (domain_name, CONFIG["redirect_path_sign_out"]),
                "Proceed",
            ),
            "status": "200",
            "headers": {
                "content-type": [
                    {"key": "Content-Type", "value": "text/html; charset=UTF-8"}
                ],
                **CONFIG.get("cloud_front_headers", {}),
            },
        }
        return response

    tokens = {
        "id_token": extracted["id_token"],
        "access_token": extracted["access_token"],
        "refresh_token": extracted["refresh_token"],
    }
    query_string = {
        "logout_uri": "https://%s%s" % (domain_name, CONFIG["redirect_path_sign_out"]),
        "client_id": CONFIG["client_id"],
    }

    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            # Redirect the user to logout
            "location": [
                {
                    "key": "location",
                    "value": "https://%s/logout?%s"
                    % (CONFIG.get("cognito_auth_domain"), urlencode(query_string)),
                }
            ],
            "set-cookie": generate_cookie_headers(
                "sign_out",
                CONFIG.get("client_id"),
                CONFIG.get("oauth_scopes"),
                tokens,
                domain_name,
                CONFIG.get("cookie_settings"),
            ),
            **CONFIG.get("cloud_front_headers", {}),
        },
    }
    return response
