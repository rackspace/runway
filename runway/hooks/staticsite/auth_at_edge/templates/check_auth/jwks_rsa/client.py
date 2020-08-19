"""Client for handling retrieval of JWKS signing keys."""
import json
import logging
import urllib

# pylint: disable=relative-beyond-top-level
from .utils import rsa_public_key_to_pem


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


class JwksClient(object):
    """Client responsible for retrieval of JWKS signing keys."""

    def __init__(self, options=None):
        """Initialize.

        Args:
            options (Optional[Dict[str, str]]): Options for the client.

        """
        self.options = options
        self.logger = logging.getLogger("__file__")

    def get_keys(self):
        """Retrieve the keys from the JWKS endpoint."""
        self.logger.info("Fetching keys from %s", self.options.get("jwks_uri"))

        try:
            request = urllib.request.urlopen(  # pylint: disable=no-member
                self.options.get("jwks_uri")
            )
            data = json.loads(
                request.read().decode(request.info().get_param("charset") or "utf-8")
            )
            keys = data["keys"]
            self.logger.info("Keys: %s", keys)
            return keys
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info("Failure: ConnectionError")
            self.logger.info(err)
            return {}

    def get_signing_key(self, kid):
        """Given a specific key id (kid) retrieve the signing key associated.

        Keyword Args:
            kid (str): The key id of the signing key.

        """
        self.logger.info("Fetching signing key for %s", kid)

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
        for key in filter(is_signing_key, keys):
            jwks.append(self.create_jwk(key))

        if not jwks:
            raise Exception("The JWKS endpoint did not contain any signing keys")

        self.logger.info("Signing Keys: %s", jwks)
        return jwks

    def create_jwk(self, key):
        """Create the JSON Web Key.

        Keyword Args:
            key (dict): The Retrieved signing key.

        """
        jwk = {"kid": key.get("kid"), "nbf": key.get("nbf")}

        if key.get("x5c"):
            # @TODO: Support certificate chains. Review library here:
            # https://github.com/auth0/node-jwks-rsa/blob/master/src/JwksClient.js#L87
            self.logger.info("X5C")
        else:
            try:
                jwk["rsaPublicKey"] = rsa_public_key_to_pem(key.get("n"), key.get("e"))
            # pylint: disable=broad-except
            except Exception as err:
                self.logger.error(err)
                jwk["rsaPublicKey"] = None
        return jwk
