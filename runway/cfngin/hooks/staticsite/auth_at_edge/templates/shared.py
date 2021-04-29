"""Shared functionality for the Auth@Edge Lambda suite."""
import base64
import hmac
import json
import logging
import re
import time
from datetime import datetime
from hashlib import sha256
from random import random
from urllib import request
from urllib.parse import urlencode

LOGGER = logging.getLogger(__name__)


def get_config():
    """Retrieve the configuration variables for the Auth@Edge suite.

    Lambda@Edge restricts the ability to use environment variables.
    This configuration object is generated with hard coded values via Runway.

    """
    # This configuration will be replaced with dynamic values
    # via the lambda_config.py Runway hook. Please review
    # that file for more information.
    config = {
        "client_id": "tbd",
        "cognito_auth_domain": "tbd",
        "cookie_settings": {},
        "http_headers": {},
        "nonce_signing_secret": "tbd",
        "oauth_scopes": [],
        "redirect_path_auth_refresh": "tbd",
        "redirect_path_sign_in": "tbd",
        "redirect_path_sign_out": "tbd",
        "required_group": "tbd",
        "user_pool_id": "tbd",
    }

    user_pool_region = "us-east-1"
    region_match = re.match(r"^(\\S+?)_\\S+$", config["user_pool_id"])
    if region_match:
        user_pool_region = region_match.groups()[0]

    config["cloud_front_headers"] = as_cloud_front_headers(config["http_headers"])
    config["token_issuer"] = "https://cognito-idp.%s.amazonaws.com/%s" % (
        user_pool_region,
        config["user_pool_id"],
    )
    config["token_jwks_uri"] = "%s/.well-known/jwks.json" % config["token_issuer"]
    return config


def as_cloud_front_headers(headers):
    """Convert a series of headers to CloudFront compliant ones.

    Args:
         headers (Dict[str, str]): The request/response headers in
            dictionary format.

    """
    res = {}
    for key, value in headers.items():
        res[key.lower()] = [{"key": key, "value": value}]
    return res


def extract_and_parse_cookies(headers, client_id, cookie_compatibility="amplify"):
    """Extract and parse the Cognito cookies from the headers.

    Args:
         headers (Dict[str, str]): The request/response headers in
            dictionary format.
        client_id (str): The Cognito UserPool Client ID.
        cookie_compatibility (str): "amplify" or "elasticsearch".

    """
    cookies = extract_cookies_from_headers(headers)
    if not cookies:
        return {}

    if cookie_compatibility == "amplify":
        cookie_names = get_amplify_cookie_names(client_id, cookies)
    elif cookie_compatibility == "elasticsearch":
        cookie_names = get_elasticsearch_cookie_names()

    return {
        "token_user_name": cookies.get(cookie_names["last_user_key"])
        if "last_user_key" in cookie_names
        else None,
        "id_token": cookies.get(cookie_names["id_token_key"]),
        "access_token": cookies.get(cookie_names["access_token_key"]),
        "refresh_token": cookies.get(cookie_names["refresh_token_key"]),
        "scopes": cookies.get(cookie_names["scope_key"])
        if "scope_key" in cookie_names
        else None,
        "nonce": cookies.get("spa-auth-edge-nonce"),
        "nonce_hmac": cookies.get("spa-auth-edge-nonce-hmac"),
        "pkce": cookies.get("spa-auth-edge-pkce"),
    }


def extract_cookies_from_headers(headers):
    """Extract all cookies from the response headers.

    Args:
         headers (Dict[str, Dict[str, str]]): The request/response headers in
            dictionary format.

    """
    if "cookie" not in headers:
        return {}

    cookies = {}
    for header in headers["cookie"]:
        split = header.get("value", "").split(";")
        for part in split:
            seq = part.split("=")
            key, value = seq[0], seq[1:]
            cookies[key.strip()] = "=".join(value).strip()

    return cookies


def decode_token(jwt):
    """Decode the JWT and load it's respective parts as JSON.

    Args:
        jwt (str): The JSON Web Token to parse/decode.

    """
    token_body = jwt.split(".")[1]
    decodable_token_body = re.sub(r"\-", "+", token_body)
    decodable_token_body = re.sub(r"\_", "/", token_body)
    decodable_token_body = base64.b64decode(decodable_token_body + "===")
    return json.loads(decodable_token_body.decode("utf8").replace("'", '"'))


def with_cookie_domain(distribution_domain_name, cookie_settings):
    """Check to see if the cookie has a domain, if not then add an Amplify JS compatible one.

    Args:
        distribution_domain_name (str): The domain name of the
            CloudFront distribution.
        cookie_settings (str): The other settings for the cookie.

    """
    try:
        cookie_settings.lower().index("domain")
        return cookie_settings
    except ValueError:
        # Add leading dot for compatibility with Amplify (js-cookie)
        return "%s; Domain=.%s" % (cookie_settings, distribution_domain_name)


def get_amplify_cookie_names(client_id, cookies_or_username):
    """Return mapping dict for cookie names for amplify."""
    key_prefix = "CognitoIdentityServiceProvider.%s" % client_id
    last_user_key = "%s.LastAuthUser" % key_prefix
    if isinstance(cookies_or_username, str):
        token_user_name = cookies_or_username
    else:
        token_user_name = cookies_or_username.get(last_user_key)
    return {
        "last_user_key": last_user_key,
        "user_data_key": "%s.%s.userData" % (key_prefix, token_user_name),
        "scope_key": "%s.%s.tokenScopesString" % (key_prefix, token_user_name),
        "id_token_key": "%s.%s.idToken" % (key_prefix, token_user_name),
        "access_token_key": "%s.%s.accessToken" % (key_prefix, token_user_name),
        "refresh_token_key": "%s.%s.refreshToken" % (key_prefix, token_user_name),
    }


def get_elasticsearch_cookie_names():
    """Return mapping dict for cookie names for elasticsearch."""
    return {
        "id_token_key": "ID-TOKEN",
        "access_token_key": "ACCESS-TOKEN",
        "refresh_token_key": "REFRESH-TOKEN",
        "cognito_enabled_key": "COGNITO-ENABLED",
    }


def generate_cookie_headers(
    event,
    client_id,
    oauth_scopes,
    tokens,
    domain_name,
    cookie_settings,
    cookie_compatibility="amplify",
):
    """Retrieve all cookie headers for our request.

    Return as CloudFront formatted headers.

    Args:
        event (str): "new_tokens" | "sign_out" | "refresh_failed".
        client_id (str): The Cognito UserPool Client ID.
        oauth_scopes (List): The scopes for oauth validation.
        tokens (Dict[str, str]): The tokens received from
            the Cognito Request (id, access, refresh).
        domain_name (str): The Domain name the cookies are
            to be associated with.
        cookie_settings (Dict[str, str]): The various settings
            that we would like for the various tokens.
        cookie_compatibility (str): "amplify" | "elasticsearch".

    """
    decoded_id_token = decode_token(tokens["id_token"])
    token_user_name = decoded_id_token.get("cognito:username")

    if cookie_compatibility == "amplify":
        cookie_names = get_amplify_cookie_names(client_id, token_user_name)
        user_data = {
            "UserAttributes": [
                {"Name": "sub", "Value": decoded_id_token.get("sub")},
                {"Name": "email", "Value": decoded_id_token.get("email")},
            ],
            "Username": token_user_name,
        }

        cookies = {
            cookie_names["last_user_key"]: "%s; %s"
            % (
                token_user_name,
                with_cookie_domain(domain_name, cookie_settings.get("idToken")),
            ),
            cookie_names["scope_key"]: "%s; %s"
            % (
                " ".join(oauth_scopes),
                with_cookie_domain(domain_name, cookie_settings.get("accessToken")),
            ),
            cookie_names["user_data_key"]: "%s; %s"
            % (
                urlencode(user_data),
                with_cookie_domain(domain_name, cookie_settings.get("idToken")),
            ),
            "amplify-signin-with-hostedUI": "true; %s"
            % (with_cookie_domain(domain_name, cookie_settings.get("accessToken"))),
        }
    elif cookie_compatibility == "elasticsearch":
        cookie_names = get_elasticsearch_cookie_names()
        cookies = {
            cookie_names["cognito_enabled_key"]: "True; %s"
            % with_cookie_domain(domain_name, cookie_settings.get("cognitoEnabled")),
        }
    cookies[cookie_names["id_token_key"]] = "%s; %s" % (
        tokens.get("id_token"),
        with_cookie_domain(domain_name, cookie_settings.get("idToken")),
    )
    cookies[cookie_names["access_token_key"]] = "%s; %s" % (
        tokens.get("access_token"),
        with_cookie_domain(domain_name, cookie_settings.get("accessToken")),
    )
    cookies[cookie_names["refresh_token_key"]] = "%s; %s" % (
        tokens.get("refresh_token"),
        with_cookie_domain(domain_name, cookie_settings.get("refreshToken")),
    )

    if event == "sign_out":
        for key in cookies:
            cookies[key] = expire_cookie(cookies[key])
    elif event == "refresh_failed":
        cookies[cookie_names["refresh_token_key"]] = expire_cookie(
            cookies[cookie_names["refresh_token_key"]]
        )

    # https://github.com/aws-samples/cloudfront-authorization-at-edge/issues/89
    for i in ["spa-auth-edge-nonce", "spa-auth-edge-nonce-hmac", "spa-auth-edge-pkce"]:
        if i in cookies:
            cookies[i] = expire_cookie(cookies[i])

    # Return cookies in the form of CF headers
    return [
        {"key": "set-cookie", "value": "%s=%s" % (key, val)}
        for key, val in cookies.items()
    ]


def expire_cookie_filter(cookie):
    """Filter to determine if a cookie starts with 'max-age' or 'expires'.

    Args:
        cookie (str): The cookie to filter.

    """
    if cookie.lower().startswith("max-age") or cookie.lower().startswith("expires"):
        return False
    return True


def expire_cookie(cookie):
    """Add an expiration property to a specific cookie.

    Args:
        cookie (str): The cookie string.

    """
    cookie_parts = cookie.split(";")
    mapped = [c.strip() for c in cookie_parts]
    filtered = filter(expire_cookie_filter, mapped)
    listed = list(filtered)
    _, settings = listed[0], listed[1:]
    settings.insert(0, "")
    settings.append("Expires=%s" % datetime.utcnow())
    return "; ".join(settings)


def http_post_with_retry(url, data, headers):
    """Given a URL/Data/Headers make a POST request with exponential backoff.

    Used for retrieving token information from Cognito

    Args:
        url (str): The URL to make the POST request to.
        data (Dict[str, str]): The dictionary of data elements to
            send with the request (urlencoded internally).
        headers (Dict[str, str]): Any headers to send with
            the POST request.

    """
    attempts = 1
    while attempts:
        try:
            encoded_data = urlencode(data).encode()
            req = request.Request(url, encoded_data, headers)
            res = request.urlopen(req).read()
            read = res.decode("utf-8")
            json_data = json.loads(read)
            return json_data
        # pylint: disable=broad-except
        except Exception as err:
            LOGGER.error("HTTP POST to %s failed (attempt %s)", url, attempts)
            LOGGER.error(err)
            if attempts >= 5:
                raise
            if attempts >= 2:
                # After attempting twice do some exponential backoff with jitter
                time.sleep((25 * (pow(2, attempts) + random() * attempts)) / 1000)
        finally:
            attempts += 1


def create_error_html(title, message, link_uri, link_text):
    """Create a basic error html page for exception returns.

    Args:
        title (str): The title of the page.
        message (str): Any exception message.
        link_uri (str): Link url.
        link_text (str): Link displayed text.

    """
    return (
        "<!DOCTYPE html>"
        + "<html lang='en'>"
        + "    <head>"
        + "        <meta charset='utf-8'>"
        + "        <title>%s</title>" % title
        + "    </head>"
        + "    <body>"
        + "        <h1>%s</h1>" % title
        + "        <p>%s</p>" % message
        + "        <a href='%s'>%s</a>" % (link_uri, link_text)
        + "    </body>"
        + "</html>"
    )


def timestamp_in_seconds():
    """Return int of current unix time."""
    return round(time.time())


def sign(string_to_sign, secret, signature_length=16):
    """Create HMAC signature for string."""
    hashed = hmac.new(bytes(secret, "ascii"), bytes(string_to_sign, "ascii"), sha256)
    return base64.urlsafe_b64encode(hashed.digest()).decode()[0:signature_length]
