
"""Check the authorization information passed along via the cookie headers.

When the information is not present or an error occurs due to verification a new
request to Cognito will be made to authorize the user. The user will be taken
to the Cognito login page to enter their information, and so long as it is valid,
the information will be passed to the parsing agent.

If a refresh token exists and it has expired (after 1 hour) do an automatic refresh
of the credentials by redirecting the user to the refresh agent.
"""
import base64
import datetime
import hashlib
import json
import logging
import secrets  # pylint: disable=import-error
import re
from urllib.parse import quote_plus, urlencode  # noqa pylint: disable=no-name-in-module, import-error

from jose import jwt  # pylint: disable=import-error

from jwks_rsa.client import JwksClient  # pylint: disable=import-error
from shared import decode_token, extract_and_parse_cookies, get_config  # noqa pylint: disable=import-error

LOGGER = logging.getLogger(__file__)

SECRET_ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
NONCE_LENGTH = 16
PKCE_LENGTH = 43
CONFIG = get_config()


def handler(event, _context):
    """Handle the request passed in.

    Keyword Args:
        event (Dict[str, Any]): The Lambda Event
    """
    request = event['Records'][0]['cf']['request']
    domain_name = request['headers']['host'][0]['value']
    querystring = request.get('querystring')
    request_query_string = (
        "?%s" % querystring
    ) if querystring else ""
    requested_uri = '%s%s' % (request['uri'], request_query_string)
    nonce = generate_nonce()

    try:
        # Extract the cookies received from Cognito
        extracted = extract_and_parse_cookies(
            request['headers'],
            CONFIG['client_id']
        )
        token_user_name = extracted.get('tokenUserName')
        id_token = extracted.get('idToken')
        refresh_token = extracted.get('refreshToken')

        # If the token user name or id token are missing then we need
        # new credentials
        if not token_user_name or not id_token:
            msg = "No valid credentials present in cookies"
            LOGGER.error(msg)
            raise Exception(msg)

        # Get the expiration date from the id token.
        decoded_token = decode_token(id_token)
        expiration = decoded_token.get('exp')
        exp_date = datetime.datetime.fromtimestamp(expiration)
        now = datetime.datetime.now()

        # If we have a refresh token and the expiration date has passed
        # then forward the user to the refresh agent
        if now > exp_date and refresh_token:
            headers = {
                # Redirect the user to the refresh agent
                'location': [
                    {
                        'key': 'location',
                        'value': 'https://%s%s?%s' % (
                            domain_name,
                            CONFIG.get('redirect_path_auth_refresh'),
                            urlencode({
                                'requestedUri': requested_uri,
                                'nonce': nonce
                            })
                        )
                    }
                ],
                'set-cookie': [
                    # Set the Nonce Cookie
                    {
                        'key': 'set-cookie',
                        'value': 'spa-auth-edge-nonce=%s; %s' % (
                            quote_plus(nonce),
                            CONFIG.get('cookie_settings').get('nonce')
                        )
                    }
                ]
            }
            # Add all CloudFrontHeaders
            headers.update(CONFIG.get('cloud_front_headers'))
            return {
                'status': '307',
                'statusDescription': 'Temporary Redirect',
                'headers': headers
            }

        # Validate the token information against the Cognito JWKS
        validate_jwt(
            id_token,
            CONFIG.get('token_jwks_uri'),
            CONFIG.get('token_issuer'),
            CONFIG.get('client_id'))

        return request
    # We need new authorization. Get the user over to Cognito
    except Exception: # noqa pylint: disable=broad-except
        pkce, pkce_hash = generate_pkce_verifier()
        payload = {
            'redirect_uri': 'https://%s%s' % (domain_name, CONFIG['redirect_path_sign_in']),
            'response_type': 'code',
            'client_id': CONFIG["client_id"],
            'state': base64.urlsafe_b64encode(
                bytes(json.dumps({
                    "nonce": nonce,
                    "requestedUri": requested_uri
                }).encode())
            ),
            'scope': " ".join(CONFIG['oauth_scopes']),
            'code_challenge_method': "S256",
            'code_challenge': pkce_hash
        }
        login_query_string = urlencode(payload, quote_via=quote_plus)
        headers = CONFIG.get('cloud_front_headers')
        headers['location'] = [
            {
                'key': 'location',
                'value': 'https://%s/oauth2/authorize?%s' % (
                    CONFIG['cognito_auth_domain'],
                    login_query_string
                )
            }
        ]
        headers['set-cookie'] = [
            # Set Nonce Cookie
            {
                'key': 'set-cookie',
                'value': 'spa-auth-edge-nonce=%s; %s' % (
                    quote_plus(nonce),
                    CONFIG.get('cookie_settings', {}).get('nonce')
                )
            },
            # Set PKCE Cookie
            {
                'key': 'set-cookie',
                'value': 'spa-auth-edge-pkce=%s; %s' % (
                    quote_plus(pkce),
                    CONFIG.get('cookie_settings', {}).get('nonce')
                )
            },
        ]

        # Redirect user to the Cognito Login
        return {
            'status': '307',
            'statusDescription': 'Temporary Redirect',
            'headers': headers
        }


def generate_pkce_verifier():
    """Generate the PKCE verification code."""
    pkce = random_key(PKCE_LENGTH)
    pkce_hash = hashlib.sha256()
    pkce_hash.update(pkce.encode('UTF-8'))
    pkce_hash = pkce_hash.digest()
    pkce_hash_b64 = base64.b64encode(pkce_hash)
    decoded_pkce = pkce_hash_b64.decode("UTF-8")
    decoded_pkce = re.sub(r'\=', '', decoded_pkce)
    decoded_pkce = re.sub(r'\+', '-', decoded_pkce)
    decoded_pkce = re.sub(r'\/', '_', decoded_pkce)

    return [pkce, decoded_pkce]


def generate_nonce():
    """Generate a random Nonce token."""
    return random_key(NONCE_LENGTH)


def random_key(length=15):
    """Generate a random key of specified length from the allowed secret characters.

    Keyword Args:
        length (int): The length of the random key
    """
    return ''.join(secrets.choice(SECRET_ALLOWED_CHARS) for _ in range(length))


def validate_jwt(jwt_token,
                 jwks_uri,
                 issuer,
                 audience
                ):  # noqa: E124
    """Validate the JWT token against the Cognito JWKs.

    Keyword Args:
        jwt_token (str): The JSON Web Token to validate
        jwks_uri (str): The URI in which to retrieve the JSON Web Keys
        issuer (str): Issuer of the JWT
        audience (str): Audience of the JWT
    """
    token_headers = jwt.get_unverified_header(jwt_token)
    if not token_headers:
        raise Exception('Cannot Parse JWT Token Headers')

    kid = token_headers.get('kid')
    jwk = get_signing_key(jwks_uri, kid)

    return jwt.decode(
        jwt_token,
        jwk,
        algorithms=['RS256'],
        audience=audience,
        issuer=issuer,
        options={'verify_at_hash': False})


def is_rsa_signing_key(key):
    """Verify if the key specified is an RSA Public Key.

    Keyword Args:
        key (Dict): The key to filter
    """
    return "rsaPublicKey" in key


def get_signing_key(jwks_uri, kid):
    """Retrieve the signing keys from the JWKS uri that match the key id specified.

    Keyword Args:
        jwks_uri (str): The URI in which to retrieve the JWKs
        kid (str): Key ID of the signing key we are looking for
    """
    client = JwksClient({'jwks_uri': jwks_uri})
    jwk = client.get_signing_key(kid)
    return jwk.get('rsaPublicKey') if is_rsa_signing_key(jwk) else jwk.get('publicKey')
