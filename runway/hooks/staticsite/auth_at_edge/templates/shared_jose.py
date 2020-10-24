"""Shared jwt functionality for the Auth@Edge Lambda suite."""
import base64
import codecs
import json
import logging
import re
from urllib import request

from jose import jwt

LOGGER = logging.getLogger(__name__)


def prepad_signed(hex_str):
    """Given a hexadecimal string prepad with 00 if not within range.

    Args:
        hex_str (string): The hexadecimal string.

    """
    msb = hex_str[0]
    if msb < "0" or msb > "7":
        return "00%s" % hex_str
    return hex_str


def to_hex(number):
    """Convert an integer to appropriate hex.

    Args:
        number (int): The number to convert.

    """
    n_str = format(int(number), "x")
    if len(n_str) % 2:
        return "0%s" % n_str
    return n_str


def encode_length_hex(number):
    """Encode the length value to a hexadecimal.

    Args:
        number (int): The number to convert.

    """
    if number <= 127:
        return to_hex(number)
    n_hex = to_hex(number)
    length = int(128 + len(n_hex) / 2)
    return to_hex(length) + n_hex


def rsa_public_key_to_pem(modulus_b64, exponent_b64):
    """Given an modulus and exponent convert an RSA public key to public PEM.

    Args:
        modulus_b64 (string): Base64 encoded modulus.
        exponent_b64 (string): Base64 encoded exponent.

    """
    modulus = base64.urlsafe_b64decode(modulus_b64 + "===")
    exponent = base64.urlsafe_b64decode(exponent_b64 + "===")
    modulus_hex = prepad_signed(modulus.hex())
    exponent_hex = prepad_signed(exponent.hex())
    mod_len = int(len(modulus_hex) / 2)
    exp_len = int(len(exponent_hex) / 2)

    encoded_mod_len = encode_length_hex(mod_len)
    encoded_exp_len = encode_length_hex(exp_len)

    encoded_pub_key = "30"
    encoded_pub_key += encode_length_hex(
        mod_len + exp_len + len(encoded_mod_len) / 2 + len(encoded_exp_len) / 2 + 2
    )
    encoded_pub_key += "02" + encoded_mod_len + modulus_hex
    encoded_pub_key += "02" + encoded_exp_len + exponent_hex

    der = base64.b64encode(codecs.decode(encoded_pub_key, "hex"))

    pem = "-----BEGIN RSA PUBLIC KEY-----\n"
    pem += "\n".join(re.findall(".{1,64}", der.decode()))
    pem += "\n-----END RSA PUBLIC KEY-----\n"
    return pem


class JwksClient(object):
    """Client responsible for retrieval of JWKS signing keys."""

    def __init__(self, options=None):
        """Initialize.

        Args:
            options (Optional[Dict[str, str]]): Options for the client.

        """
        self.options = options

    def get_keys(self):
        """Retrieve the keys from the JWKS endpoint."""
        LOGGER.info("Fetching keys from %s", self.options.get("jwks_uri"))

        try:
            request_res = request.urlopen(  # pylint: disable=no-member
                self.options.get("jwks_uri")
            )
            data = json.loads(
                request_res.read().decode(
                    request_res.info().get_param("charset") or "utf-8"
                )
            )
            keys = data["keys"]
            LOGGER.info("Keys: %s", keys)
            return keys
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.info("Failure: ConnectionError")
            LOGGER.info(err)
            return {}

    def get_signing_key(self, kid):
        """Given a specific key id (kid) retrieve the signing key associated.

        Keyword Args:
            kid (str): The key id of the signing key.

        """
        LOGGER.info("Fetching signing key for %s", kid)

        keys = self.get_signing_keys()
        try:
            key = next(x for x in keys if x.get("kid") == kid)
            return key
        except StopIteration:
            raise Exception("Was not able to locate a key with kid %s" % kid)

    def get_signing_keys(self):
        """Given a set of keys find all that are signing keys."""
        keys = self.get_keys()

        if not keys:
            raise Exception("The JWKS endpoint did not contain any keys")

        jwks = []
        for key in filter(self.is_signing_key, keys):
            jwks.append(self.create_jwk(key))

        if not jwks:
            raise Exception("The JWKS endpoint did not contain any signing keys")

        LOGGER.info("Signing Keys: %s", jwks)
        return jwks

    @staticmethod
    def create_jwk(key):
        """Create the JSON Web Key.

        Keyword Args:
            key (dict): The Retrieved signing key.

        """
        jwk = {"kid": key.get("kid"), "nbf": key.get("nbf")}

        if key.get("x5c"):
            # @TODO: Support certificate chains. Review library here:
            # https://github.com/auth0/node-jwks-rsa/blob/master/src/JwksClient.js#L87
            LOGGER.info("X5C")
        else:
            try:
                jwk["rsaPublicKey"] = rsa_public_key_to_pem(key.get("n"), key.get("e"))
            # pylint: disable=broad-except
            except Exception as err:
                LOGGER.error(err)
                jwk["rsaPublicKey"] = None
        return jwk

    @staticmethod
    def is_signing_key(key):
        """Filter to determine if this is a signing key.

        Args:
            key (Dict[str, str]): The key.

        """
        if key.get("kty", "") != "RSA":
            return False
        if not key.get("kid", None):
            return False
        if key.get("use", "") != "sig":
            return False
        return key.get("x5c") or (key.get("n") and key.get("e"))


def is_rsa_signing_key(key):
    """Verify if the key specified is an RSA Public Key.

    Args:
        key (Dict): The key to filter.

    """
    return "rsaPublicKey" in key


def get_signing_key(jwks_uri, kid):
    """Retrieve the signing keys from the JWKS uri that match the key id specified.

    Args:
        jwks_uri (str): The URI in which to retrieve the JWKs.
        kid (str): Key ID of the signing key we are looking for.

    """
    client = JwksClient({"jwks_uri": jwks_uri})
    jwk = client.get_signing_key(kid)
    return jwk.get("rsaPublicKey") if is_rsa_signing_key(jwk) else jwk.get("publicKey")


def validate_jwt(jwt_token, jwks_uri, issuer, audience):
    """Validate the JWT token against the Cognito JWKs.

    Args:
        jwt_token (str): The JSON Web Token to validate.
        jwks_uri (str): The URI in which to retrieve the JSON Web Keys.
        issuer (str): Issuer of the JWT.
        audience (str): Audience of the JWT.

    """
    token_headers = jwt.get_unverified_header(jwt_token)
    if not token_headers:
        raise Exception("Cannot Parse JWT Token Headers")

    kid = token_headers.get("kid")
    jwk = get_signing_key(jwks_uri, kid)

    return jwt.decode(
        jwt_token,
        jwk,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
        options={"verify_at_hash": False},
    )


def validate_and_check_id_token(
    id_token, jwks_uri, issuer, audience, required_group=None
):
    """Validate JWT and (optionally) check group membership."""
    id_token_payload = validate_jwt(id_token, jwks_uri, issuer, audience)
    if required_group:
        cognito_groups = id_token_payload.get("cognito:groups")
        if not cognito_groups:
            raise MissingRequiredGroupError("Token does not have any groups")
        if required_group not in cognito_groups:
            raise MissingRequiredGroupError("Token does not have required group")


class MissingRequiredGroupError(Exception):
    """Raised when user is not in a required Cognito User Pool group."""
