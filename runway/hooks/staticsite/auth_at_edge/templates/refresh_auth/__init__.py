"""Refresh authorization token for new credentials."""
import logging
import traceback
from urllib.parse import parse_qs

from shared import (  # noqa pylint: disable=import-error
    create_error_html,
    extract_and_parse_cookies,
    generate_cookie_headers,
    get_config,
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

        cookies = extract_and_parse_cookies(request.get("headers"), CONFIG["client_id"])

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        tokens = {
            "id_token": cookies["id_token"],
            "access_token": cookies["access_token"],
            "refresh_token": cookies["refresh_token"],
        }

        validate_refresh_request(current_nonce, cookies["nonce"], tokens)

        try:
            # Request new tokens based on the refresh_token
            body = {
                "grant_type": "refresh_token",
                "client_id": CONFIG["client_id"],
                "refresh_token": tokens.get("refresh_token"),
            }
            res = http_post_with_retry(
                ("https://%s/oauth2/token" % CONFIG["cognito_auth_domain"]),
                body,
                headers,
            )
            tokens["id_token"] = res.get("id_token")
            tokens["access_token"] = res.get("access_token")
            cookie_headers_event_type = "new_tokens"
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.debug(err)
            cookie_headers_event_type = "refresh_failed"

        response = {
            "status": "307",
            "statusDescription": "Temporary Redirect",
            "headers": {
                "location": [{"key": "location", "value": redirected_from_uri}],
                "set-cookie": generate_cookie_headers(
                    cookie_headers_event_type,
                    CONFIG.get("client_id"),
                    CONFIG.get("oauth_scopes"),
                    tokens,
                    domain_name,
                    CONFIG.get("cookie_settings"),
                ),
                **CONFIG.get("cloud_front_headers", {}),
            },
        }
        # Redirect the user back to their requested uri
        # with new tokens at hand
        return response

    # Send a basic html error response and inform the user
    # why refresh was unsuccessful
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.info(err)
        LOGGER.info(traceback.print_exc())

        response = {
            "body": create_error_html(
                "Refresh issue",
                "Your sign-in refresh failed due to a technical issue: %s" % err,
                redirected_from_uri,
                "Try Again",
            ),
            "status": "400",
            "headers": {
                "content-type": [
                    {"key": "Content-Type", "value": "text/html; charset=UTF-8"}
                ],
                **CONFIG.get("cloud_front_headers", {}),
            },
        }

        return response


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
