"""Check the authorization information passed along via the cookie headers.

When the information is not present or an error occurs due to verification a new
request to Cognito will be made to authorize the user. The user will be taken
to the Cognito login page to enter their information, and as long as it is valid,
the information will be passed to the parsing agent.

If a refresh token exists and it has expired (after 1 hour) do an automatic refresh
of the credentials by redirecting the user to the refresh agent.

"""
import base64
import datetime
import hashlib
import json
import logging
import re
import secrets
from urllib.parse import quote_plus, urlencode

from shared_jose import validate_jwt  # noqa pylint: disable=import-error

from shared import (  # noqa pylint: disable=import-error
    decode_token,
    extract_and_parse_cookies,
    get_config,
    sign,
    timestamp_in_seconds,
)

LOGGER = logging.getLogger(__file__)

SECRET_ALLOWED_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)
NONCE_LENGTH = 16
PKCE_LENGTH = 43
CONFIG = get_config()


def handler(event, _context):
    """Handle the request passed in.

    Args:
        event (Dict[str, Any]): The Lambda Event.
        _context (Any): Lambda context object.

    """
    request = event["Records"][0]["cf"]["request"]
    domain_name = request["headers"]["host"][0]["value"]
    querystring = request.get("querystring")
    request_query_string = ("?%s" % querystring) if querystring else ""
    requested_uri = "%s%s" % (request["uri"], request_query_string)

    try:
        # Extract the cookies received from Cognito
        extracted = extract_and_parse_cookies(request["headers"], CONFIG["client_id"])
        token_user_name = extracted["token_user_name"]
        id_token = extracted["id_token"]
        refresh_token = extracted["refresh_token"]

        # If the token user name or id token are missing then we need
        # new credentials
        if not token_user_name or not id_token:
            msg = "No valid credentials present in cookies"
            LOGGER.error(msg)
            raise Exception(msg)

        # Get the expiration date from the id token.
        decoded_token = decode_token(id_token)
        expiration = decoded_token.get("exp")
        exp_date = datetime.datetime.fromtimestamp(expiration)
        now = datetime.datetime.now()

        # If we have a refresh token and the expiration date has passed
        # then forward the user to the refresh agent
        if now > (exp_date - datetime.timedelta(minutes=10)) and refresh_token:
            nonce = generate_nonce()
            response = {
                "status": "307",
                "statusDescription": "Temporary Redirect",
                "headers": {
                    # Redirect the user to the refresh agent
                    "location": [
                        {
                            "key": "location",
                            "value": "https://%s%s?%s"
                            % (
                                domain_name,
                                CONFIG.get("redirect_path_auth_refresh"),
                                urlencode(
                                    {"requestedUri": requested_uri, "nonce": nonce}
                                ),
                            ),
                        }
                    ],
                    "set-cookie": [
                        # Set the Nonce Cookie
                        {
                            "key": "set-cookie",
                            "value": "spa-auth-edge-nonce=%s; %s"
                            % (
                                quote_plus(nonce),
                                CONFIG.get("cookie_settings").get("nonce"),
                            ),
                        },
                        {
                            "key": "set-cookie",
                            "value": "spa-auth-edge-nonce-hmac=%s; %s"
                            % (
                                quote_plus(sign(nonce, CONFIG["nonce_signing_secret"])),
                                CONFIG.get("cookie_settings").get("nonce"),
                            ),
                        },
                    ],
                    **CONFIG.get("cloud_front_headers", {}),
                },
            }
            return response

        # Validate the token information against the Cognito JWKS
        validate_jwt(
            id_token,
            CONFIG["token_jwks_uri"],
            CONFIG["token_issuer"],
            CONFIG["client_id"],
        )

        return request
    except Exception:  # noqa pylint: disable=broad-except
        # We need new authorization. Get the user over to Cognito
        nonce = generate_nonce()
        state = {
            "nonce": nonce,
            "nonceHmac": sign(nonce, CONFIG["nonce_signing_secret"]),
            **generate_pkce_verifier(),
        }
        login_query_string = urlencode(
            {
                "redirect_uri": "https://%s%s"
                % (domain_name, CONFIG["redirect_path_sign_in"]),
                "response_type": "code",
                "client_id": CONFIG["client_id"],
                "state": base64.urlsafe_b64encode(
                    bytes(
                        json.dumps(
                            {"nonce": state["nonce"], "requestedUri": requested_uri}
                        ).encode()
                    )
                ),
                "scope": " ".join(CONFIG["oauth_scopes"]),
                "code_challenge_method": "S256",
                "code_challenge": state["pkceHash"],
            },
            quote_via=quote_plus,
        )
        # Redirect user to the Cognito Login
        response = {
            "status": "307",
            "statusDescription": "Temporary Redirect",
            "headers": {
                "location": [
                    {
                        "key": "location",
                        "value": "https://%s/oauth2/authorize?%s"
                        % (CONFIG["cognito_auth_domain"], login_query_string),
                    }
                ],
                "set-cookie": [
                    {
                        "key": "set-cookie",
                        "value": "spa-auth-edge-nonce=%s; %s"
                        % (
                            quote_plus(state["nonce"]),
                            CONFIG.get("cookie_settings", {}).get("nonce"),
                        ),
                    },
                    {
                        "key": "set-cookie",
                        "value": "spa-auth-edge-nonce-hmac=%s; %s"
                        % (
                            quote_plus(state["nonceHmac"]),
                            CONFIG.get("cookie_settings", {}).get("nonce"),
                        ),
                    },
                    {
                        "key": "set-cookie",
                        "value": "spa-auth-edge-pkce=%s; %s"
                        % (
                            quote_plus(state["pkce"]),
                            CONFIG.get("cookie_settings", {}).get("nonce"),
                        ),
                    },
                ],
                **CONFIG.get("cloud_front_headers", {}),
            },
        }
        return response


def generate_pkce_verifier():
    """Generate the PKCE verification code."""
    pkce = random_key(PKCE_LENGTH)
    pkce_hash = hashlib.sha256()
    pkce_hash.update(pkce.encode("UTF-8"))
    pkce_hash = pkce_hash.digest()
    pkce_hash_b64 = base64.b64encode(pkce_hash)
    decoded_pkce = pkce_hash_b64.decode("UTF-8")
    decoded_pkce = re.sub(r"\=", "", decoded_pkce)
    decoded_pkce = re.sub(r"\+", "-", decoded_pkce)
    decoded_pkce = re.sub(r"\/", "_", decoded_pkce)

    return {"pkce": pkce, "pkceHash": decoded_pkce}


def generate_nonce():
    """Generate a random Nonce token."""
    return str(timestamp_in_seconds()) + "T" + random_key(NONCE_LENGTH)


def random_key(length=15):
    """Generate a random key of specified length from the allowed secret characters.

    Args:
        length (int): The length of the random key.

    """
    return "".join(secrets.choice(SECRET_ALLOWED_CHARS) for _ in range(length))
