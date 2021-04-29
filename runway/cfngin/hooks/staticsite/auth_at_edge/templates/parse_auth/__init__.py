"""Parse the given Cognito/Local authorization information.

Ensure the parsed Cognito and Local authorization information from the retrieved
query string parameter and cookie headers matches expectations. If it doesn't
then inform the user of a bad request, otherwise retrieve the Cognito tokens to
add to the cookie headers.
"""

import base64
import hmac
import json
import logging
from datetime import datetime
from urllib.parse import parse_qs

from shared_jose import (  # noqa pylint: disable=import-error
    MissingRequiredGroupError,
    validate_and_check_id_token,
)

from shared import (  # noqa pylint: disable=import-error
    create_error_html,
    extract_and_parse_cookies,
    generate_cookie_headers,
    get_config,
    http_post_with_retry,
    sign,
    timestamp_in_seconds,
)

LOGGER = logging.getLogger(__name__)
CONFIG = get_config()
COGNITO_TOKEN_ENDPOINT = "https://%s/oauth2/token" % CONFIG["cognito_auth_domain"]
NONCE_MAX_AGE = 60 * 60 * 24


class RequiresConfirmationError(Exception):
    """Raised when user needs to be sent back to Cognito."""


def validate_querystring_and_cookies(request, cookies):
    """Handle the authorization parsing.

    Args:
        request (Any): Cloudfront request.
        cookies (Dict[str, Any]): Cookies.

    """
    qsp = parse_qs(request.get("querystring"))
    # Authorization code given by Cognito
    code = qsp.get("code")
    # The requested URI and current nonce information
    state = json.loads(base64.urlsafe_b64decode(qsp.get("state")[0]).decode())

    if qsp.get("error"):
        raise Exception(
            "[Cognito] %s: %s" % (qsp["error"], qsp.get("error_description"))
        )

    # Missing required components
    if not code or not state:
        msg = (
            "Invalid query string. "
            'Your query string should include parameters "state" and "code" '
            "(this can be caused by authentication attempts originating from "
            "this site, which is not allowed)"
        )
        LOGGER.info(msg)
        raise Exception(msg)

    current_nonce = state.get("nonce")
    requested_uri = state.get("requestedUri", "")

    # Retrieve the original nonce value as well as our PKCE code
    original_nonce = cookies["nonce"]
    pkce = cookies["pkce"]
    nonce_hmac = cookies["nonce_hmac"]

    # If we're missing one of the nonces, or they don't match, cause an error
    if not current_nonce or not original_nonce or current_nonce != original_nonce:
        # No original nonce? CSRF violation
        if not original_nonce:
            msg = (
                "Your browser didn't send the nonce cookie along, "
                "but it is required for security (prevent CSRF)"
            )
            LOGGER.debug(msg)
            raise RequiresConfirmationError(msg)
        # Nonce's don't match
        msg = "Nonce mismatch (multiple parallel authentication attempts?)"
        LOGGER.debug(msg)
        raise RequiresConfirmationError(msg)
    if not pkce:
        raise Exception(
            "Your browser didn't send the pkce cookie along, "
            "but it is required for security (prevent CSRF)"
        )

    # Nonce should not be too old
    nonce_timestamp = int(current_nonce.split("T")[0])
    if (timestamp_in_seconds() - nonce_timestamp) > NONCE_MAX_AGE:
        raise RequiresConfirmationError(
            "Nonce is too old (nonce timestnonce_timestampamp is %s)"
            % datetime.fromtimestamp(nonce_timestamp).isoformat()
        )

    # Check nonce signature to ensure we generated it
    calculated_hmac = sign(current_nonce, CONFIG["nonce_signing_secret"])
    if not hmac.compare_digest(calculated_hmac, nonce_hmac):
        raise RequiresConfirmationError(
            "Nonce signature mismatch; expected %s but got %s"
            % (calculated_hmac, nonce_hmac)
        )

    return [code, pkce, requested_uri]


def handler(event, _context):
    """Handle the authorization parsing.

    Args:
        event (Any): The Lambda Event.
        _context (Any): Lambda context object.

    """
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    redirected_from_uri = "https://%s" % domain_name
    id_token = None

    # Attempt to parse the request and retrieve authorization
    # tokens to integrate with our header cookies
    try:
        # Get all the cookies from the headers
        cookies = extract_and_parse_cookies(request.get("headers"), CONFIG["client_id"])
        id_token = cookies["id_token"]
        code, pkce, requested_uri = validate_querystring_and_cookies(request, cookies)
        redirected_from_uri += requested_uri

        # Request tokens from our Cognito Authorization Domain
        body = {
            "grant_type": "authorization_code",
            "client_id": CONFIG["client_id"],
            "redirect_uri": "https://%s%s"
            % (domain_name, CONFIG.get("redirect_path_sign_in")),
            "code": code[0],
            "code_verifier": pkce,
        }
        tokens = http_post_with_retry(
            COGNITO_TOKEN_ENDPOINT,
            body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not tokens:
            raise Exception("Was not able to obtain tokens from Cognito")

        # Validate the token information against the Cognito JWKS
        # (and ensure group membership, if applicable)
        validate_and_check_id_token(
            tokens["id_token"],
            CONFIG["token_jwks_uri"],
            CONFIG["token_issuer"],
            CONFIG["client_id"],
            CONFIG.get("required_group"),
        )

        # Redirect user to the originally requested uri with the
        # token header cookies
        response = {
            "status": "307",
            "statusDescription": "Temporary Redirect",
            "headers": {
                "location": [{"key": "location", "value": redirected_from_uri}],
                "set-cookie": generate_cookie_headers(
                    "new_tokens",
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
    except Exception as err:  # pylint: disable=broad-except
        if id_token:
            # ID token found; checking if it is valid
            try:
                validate_and_check_id_token(
                    id_token,
                    CONFIG["token_jwks_uri"],
                    CONFIG["token_issuer"],
                    CONFIG["client_id"],
                    CONFIG.get("required_group"),
                )
                # Token is valid; return user to where they came from
                return {
                    "status": "307",
                    "statusDescription": "Temporary Redirect",
                    "headers": {
                        "location": [{"key": "location", "value": redirected_from_uri}],
                        **CONFIG.get("cloud_front_headers", {}),
                    },
                }
            except Exception as err:  # pylint: disable=broad-except
                LOGGER.debug("Id token not valid")
                LOGGER.debug(err)

        if isinstance(err, RequiresConfirmationError):
            html_params = [
                "Confirm sign-in",
                "We need your confirmation to sign you (%s)" % str(err),
                redirected_from_uri,
                "Confirm",
            ]
        elif isinstance(err, MissingRequiredGroupError):
            html_params = [
                "Not Authorized",
                "Your user is not authorized for this site. Please contact the admin.",
                redirected_from_uri,
                "Try Again",
            ]
        else:
            html_params = [
                "Sign-in issue",
                "Sign-in unsuccessful because of a technical problem: %s" % str(err),
                redirected_from_uri,
                "Try Again",
            ]

        # Inform user of bad request and reason
        return {
            "body": create_error_html(*html_params),
            "status": "200",
            "headers": {
                **CONFIG.get("cloud_front_headers", {}),
                "content-type": [
                    {"key": "Content-Type", "value": "text/html; charset=UTF-8"}
                ],
            },
        }
