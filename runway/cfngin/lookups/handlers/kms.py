"""AWS KMS lookup."""
# pylint: disable=arguments-differ,unused-argument
import codecs

from runway.lookups.handlers.base import LookupHandler

from ...session_cache import get_session
from ...util import read_value_from_path

TYPE_NAME = "kms"


class KmsLookup(LookupHandler):
    """AWS KMS lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        r"""Decrypt the specified value with a master key in KMS.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        ``value`` should be in the following format:

            [<region>@]<base64 encrypted value>

        .. note: The region is optional, and defaults to the environment's
                 ``AWS_DEFAULT_REGION`` if not specified.

        Example:
            ::

                # We use the aws cli to get the encrypted value for the string
                # "PASSWORD" using the master key called "myKey" in
                # us-east-1
                $ aws --region us-east-1 kms encrypt --key-id alias/myKey \
                        --plaintext "PASSWORD" --output text --query CiphertextBlob

                CiD6bC8t2Y<...encrypted blob...>

                # With CFNgin we would reference the encrypted value like:
                conf_key: ${kms us-east-1@CiD6bC8t2Y<...encrypted blob...>}

            You can optionally store the encrypted value in a file, ie::

                kms_value.txt
                us-east-1@CiD6bC8t2Y<...encrypted blob...>

            and reference it within CFNgin (NOTE: the path should be relative
            to the CFNgin config file)::

                conf_key: ${kms file://kms_value.txt}

                # Both of the above would resolve to
                conf_key: PASSWORD

        """
        value = read_value_from_path(value)

        region = None
        if "@" in value:
            region, value = value.split("@", 1)

        kms = get_session(region).client("kms")

        # encode str value as an utf-8 bytestring for use with codecs.decode.
        value = value.encode("utf-8")

        # get raw but still encrypted value from base64 version.
        decoded = codecs.decode(value, "base64")

        # decrypt and return the plain text raw value.
        return kms.decrypt(CiphertextBlob=decoded)["Plaintext"]
