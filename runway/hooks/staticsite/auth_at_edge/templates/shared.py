"""Shared functionality for the Auth@Edge Lambda suite."""
import base64
import json
import logging
import re
import time
import traceback
from datetime import datetime
from random import random
from urllib import request  # pylint: disable=no-name-in-module
from urllib.parse import urlencode  # pylint: disable=no-name-in-module,import-error

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
        "oauth_scopes": [],
        "redirect_path_auth_refresh": "tbd",
        "redirect_path_sign_in": "tbd",
        "redirect_path_sign_out": "tbd",
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


def extract_and_parse_cookies(headers, client_id):
    """Extract and parse the Cognito cookies from the headers.

    Args:
         headers (Dict[str, str]): The request/response headers in
            dictionary format.
        client_id (str): The Cognito UserPool Client ID.

    """
    cookies = extract_cookies_from_headers(headers)

    if not cookies:
        return {}

    key_prefix = "CognitoIdentityServiceProvider.%s" % client_id
    last_user_key = "%s.LastAuthUser" % key_prefix
    token_user_name = cookies.get(last_user_key, "")

    scope_key = "%s.%s.tokenScopesString" % (key_prefix, token_user_name)
    scopes = cookies.get(scope_key, "")

    id_token_key = "%s.%s.idToken" % (key_prefix, token_user_name)
    id_token = cookies.get(id_token_key, "")

    access_token_key = "%s.%s.accessToken" % (key_prefix, token_user_name)
    access_token = cookies.get(access_token_key, "")

    refresh_token_key = "%s.%s.refreshToken" % (key_prefix, token_user_name)
    refresh_token = cookies.get(refresh_token_key, "")

    return {
        "tokenUserName": token_user_name,
        "idToken": id_token,
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "scopes": scopes,
        "nonce": cookies.get("spa-auth-edge-nonce", ""),
        "pkce": cookies.get("spa-auth-edge-pkce", ""),
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


def get_cookie_headers(
    client_id,
    oauth_scopes,
    tokens,
    domain_name,
    cookie_settings,
    expire_all_tokens=False,
):
    """Retrieve all cookie headers for our request.

    Return as CloudFront formatted headers.

    Args:
        client_id (str): The Cognito UserPool Client ID.
        oauth_scopes (List): The scopes for oauth validation.
        tokens (Dict[str, str]): The tokens received from
            the Cognito Request (id, access, refresh).
        domain_name (str): The Domain name the cookies are
            to be associated with.
        cookie_settings (Dict[str, str]): The various settings
            that we would like for the various tokens.
        expire_all_tokens (Optional[bool]): Whether to expire
            all Cognito tokens.

    """
    decoded_id_token = decode_token(tokens["id_token"])
    token_user_name = decoded_id_token.get("cognito:username")
    key_prefix = "CognitoIdentityServiceProvider.%s" % client_id
    key_and_user_prefix = "%s.%s" % (key_prefix, token_user_name)
    id_token_key = "%s.idToken" % key_and_user_prefix
    access_token_key = "%s.accessToken" % key_and_user_prefix
    refresh_token_key = "%s.refreshToken" % key_and_user_prefix
    last_user_key = "%s.LastAuthUser" % key_prefix
    scope_key = "%s.tokenScopesString" % key_and_user_prefix
    scopes_string = " ".join(oauth_scopes)
    user_data_key = "%s.userData" % key_and_user_prefix
    user_data = {
        "UserAttributes": [
            {"Name": "sub", "Value": decoded_id_token.get("sub")},
            {"Name": "email", "Value": decoded_id_token.get("email")},
        ],
        "Username": token_user_name,
    }

    cookies = {
        id_token_key: "%s; %s"
        % (
            tokens.get("id_token"),
            with_cookie_domain(domain_name, cookie_settings.get("idToken")),
        ),
        access_token_key: "%s; %s"
        % (
            tokens.get("access_token"),
            with_cookie_domain(domain_name, cookie_settings.get("accessToken")),
        ),
        refresh_token_key: "%s; %s"
        % (
            tokens.get("refresh_token"),
            with_cookie_domain(domain_name, cookie_settings.get("refreshToken")),
        ),
        last_user_key: "%s; %s"
        % (
            token_user_name,
            with_cookie_domain(domain_name, cookie_settings.get("idToken")),
        ),
        scope_key: "%s; %s"
        % (
            scopes_string,
            with_cookie_domain(domain_name, cookie_settings.get("accessToken")),
        ),
        user_data_key: "%s; %s"
        % (
            urlencode(user_data),
            with_cookie_domain(domain_name, cookie_settings.get("idToken")),
        ),
        "amplify-signin-with-hostedUI": "true; %s"
        % (with_cookie_domain(domain_name, cookie_settings.get("accessToken"))),
    }

    if expire_all_tokens:
        for key in cookies:
            cookies[key] = expire_cookie(cookies[key])
    elif not tokens.get("refresh_token"):
        cookies[refresh_token_key] = expire_cookie(cookies[refresh_token_key])

    cloud_front_headers = []
    for key, val in cookies.items():
        cloud_front_headers.append({"key": "set-cookie", "value": "%s=%s" % (key, val)})

    return cloud_front_headers


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
        headers (List[Dict[str, str]]): Any headers to send with
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
            LOGGER.error(traceback.print_exc())
            if attempts >= 5:
                break
            if attempts >= 2:
                # After attempting twice do some exponential backoff with jitter
                time.sleep((25 * (pow(2, attempts) + random() * attempts)) / 1000)
        finally:
            attempts += 1


def create_error_html(title, message, try_again_href):
    """Create a basic error html page for exception returns.

    Args:
        title (str): The title of the page.
        message (str): Any exception message.
        try_again_href (str): URL href to try the request again.

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
        + "        <p><b>ERROR:</b> %s</p>" % message
        + "        <a href='%s'>Try again</a>" % try_again_href
        + "    </body>"
        + "</html>"
    )
