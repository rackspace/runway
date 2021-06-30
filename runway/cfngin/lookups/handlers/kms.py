"""AWS KMS lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import codecs
from typing import TYPE_CHECKING, Any, BinaryIO, Union, cast

from ....lookups.handlers.base import LookupHandler
from ...utils import read_value_from_path

if TYPE_CHECKING:
    from ....context import CfnginContext

TYPE_NAME = "kms"


class KmsLookup(LookupHandler):
    """AWS KMS lookup."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, **_: Any
    ) -> str:
        r"""Decrypt the specified value with a master key in KMS.

        Args:
            value: Parameter(s) given to this lookup.
            context: Context instance.

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

        kms = context.get_session(region=region).client("kms")

        # get raw but still encrypted value from base64 version.
        decoded = codecs.decode(value.encode(), "base64")

        # decrypt and return the plain text raw value.
        decrypted = cast(
            Union[BinaryIO, bytes],
            kms.decrypt(CiphertextBlob=decoded).get("Plaintext", b""),
        )
        if isinstance(decrypted, bytes):
            return decrypted.decode()
        return decrypted.read().decode()
