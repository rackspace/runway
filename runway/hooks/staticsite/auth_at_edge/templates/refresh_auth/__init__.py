"""Refresh authorization token for new credentials."""
import logging
import traceback
from urllib.parse import parse_qs  # noqa pylint: disable=E

from shared import (  # noqa pylint: disable=import-error
    create_error_html,
    extract_and_parse_cookies,
    get_config,
    get_cookie_headers,
    http_post_with_retry,
)

LOGGER = logging.getLogger(__name__)
CONFIG = get_config()


def handler(event, _context):
    """Handle the authorization refresh.

    Args:
        event: The Lambda Event.
        _context (Any): Lambda context object.

    """
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    redirected_from_uri = "https://%s" % domain_name

    try:
        parsed_qs = parse_qs(request.get("querystring"))
        requested_uri = parsed_qs.get("requestedUri")[0]
        current_nonce = parsed_qs.get("nonce")[0]
        # Add the requested uri path to the main
        redirected_from_uri += requested_uri or ""

        cookies = extract_and_parse_cookies(
            request.get("headers"), CONFIG.get("client_id")
        )

        tokens = {
            "id_token": cookies.get("idToken"),
            "access_token": cookies.get("accessToken"),
            "refresh_token": cookies.get("refreshToken"),
        }

        validate_refresh_request(current_nonce, cookies.get("nonce"), tokens)

        try:
            # Request new tokens based on the refresh_token
            body = {
                "grant_type": "refresh_token",
                "client_id": CONFIG.get("client_id"),
                "refresh_token": tokens.get("refresh_token"),
            }
            res = http_post_with_retry(
                ("https://%s/oauth2/token" % CONFIG.get("cognito_auth_domain")),
                body,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            tokens["id_token"] = res.get("id_token")
            tokens["access_token"] = res.get("access_token")
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.error(err)
            # Otherwise clear the refresh token
            tokens["refresh_token"] = ""

        headers = {
            "location": [{"key": "location", "value": redirected_from_uri}],
            "set-cookie": get_cookie_headers(
                CONFIG.get("client_id"),
                CONFIG.get("oauth_scopes"),
                tokens,
                domain_name,
                CONFIG.get("cookie_settings"),
            ),
        }
        headers.update(CONFIG.get("cloud_front_headers"))

        # Redirect the user back to their requested uri
        # with new tokens at hand
        return {
            "status": "307",
            "statusDescription": "Temporary Redirect",
            "headers": headers,
        }

    # Send a basic html error response and inform the user
    # why refresh was unsuccessful
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.info(err)
        LOGGER.info(traceback.print_exc())

        headers = {
            "content-type": [
                {"key": "Content-Type", "value": "text/html; charset=UTF-8"}
            ]
        }
        headers.update(CONFIG.get("cloud_front_headers"))

        return {
            "body": create_error_html("Bad Request", err, redirected_from_uri),
            "status": "400",
            "headers": headers,
        }


def validate_refresh_request(current_nonce, original_nonce, tokens):
    """Validate that nonce and tokens are present.

    Args:
        current_nonce (str): The current nonce code.
        original_nonce (str): The original nonce code.
        tokens (Dict[str, str]): A dictionary of all the token_types
            and their corresponding token values (id, auth, refresh).

    """
    if not original_nonce:
        msg = (
            "Your browser didn't send the nonce cookie along, "
            "but it is required for security (prevent CSRF)."
        )
        LOGGER.error(msg)
        raise Exception(msg)

    if current_nonce != original_nonce:
        msg = "Nonce mismatch"
        LOGGER.error(msg)
        raise Exception(msg)

    for token_type, token in tokens.items():
        if not token:
            msg = "Missing %s" % token_type
            LOGGER.error(msg)
            raise Exception(msg)
