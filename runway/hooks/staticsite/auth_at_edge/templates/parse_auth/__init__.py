"""Parse the given Cognito/Local authorization information.

Ensure the parsed Cognito and Local authorization information from the retrieved
query string parameter and cookie headers matches expectations. If it doesn't
then inform the user of a bad request, otherwise retrieve the Cognito tokens to
add to the cookie headers.
"""

import base64
import json
import logging
import traceback
from urllib.parse import parse_qs  # noqa pylint: disable=no-name-in-module,import-error

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
    """Handle the authorization parsing.

    Args:
        event (Any): The Lambda Event.
        _context (Any): Lambda context object.

    """
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    redirected_from_uri = "https://%s" % domain_name

    # Attempt to parse the request and retrieve authorization
    # tokens to integrate with our header cookies
    try:
        qsp = parse_qs(request.get("querystring"))
        # Authorization code given by Cognito
        code = qsp.get("code")
        # The requested URI and current nonce information
        state = json.loads(base64.urlsafe_b64decode(qsp.get("state")[0]).decode())

        # Missing required components
        if not code or not state:
            msg = (
                "Invalid query string. "
                'Your query string should include parameters "state" and "code"'
            )
            LOGGER.info(msg)
            raise Exception(msg)

        current_nonce = state.get("nonce")
        requested_uri = state.get("requestedUri")
        redirected_from_uri = requested_uri or "/"
        # Get all the cookies from the headers
        cookies = extract_and_parse_cookies(
            request.get("headers"), CONFIG.get("client_id")
        )
        # Retrieve the original nonce value as well as our PKCE code
        original_nonce = cookies.get("nonce")
        pkce = cookies.get("pkce")

        # If we're missing one of the nonces, or they don't match, cause an error
        if not current_nonce or not original_nonce or current_nonce != original_nonce:
            # No original nonce? CSRF violation
            if not original_nonce:
                msg = (
                    "Your browser didn't send the nonce cookie along, "
                    "but it is required for security (prevent CSRF)"
                )
                LOGGER.error(msg)
                raise Exception(msg)
            # Nonce's don't match
            msg = "Nonce Mismatch"
            LOGGER.error(msg)
            raise Exception(msg)

        payload = {
            "grant_type": "authorization_code",
            "client_id": CONFIG.get("client_id"),
            "redirect_uri": "https://%s%s"
            % (domain_name, CONFIG.get("redirect_path_sign_in")),
            "code": code[0],
            "code_verifier": pkce,
        }

        # Request tokens from our Cognito Authorization Domain
        tokens = http_post_with_retry(
            ("https://%s/oauth2/token" % CONFIG.get("cognito_auth_domain")),
            payload,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not tokens:
            raise Exception("Was not able to obtain tokens from Cognito")

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
        # Redirect user to the originally requested uri with the
        # token header cookies
        response = {
            "status": "307",
            "statusDescription": "Temporary Redirect",
            "headers": headers,
        }
        return response
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error(err)
        LOGGER.error(traceback.print_exc())

        headers = CONFIG.get("cloud_front_headers")
        headers["content-type"] = [
            {"key": "Content-Type", "value": "text/html; charset=UTF-8"}
        ]

        # Inform user of bad request and reason
        return {
            "body": create_error_html("Bad Request", err, redirected_from_uri),
            "status": "400",
            "headers": headers,
        }
