"""AWS KMS lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import codecs
import logging
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, Tuple, Union, cast

from typing_extensions import Final, Literal

from ....lookups.handlers.base import LookupHandler
from ....utils import DOC_SITE
from ...utils import read_value_from_path

if TYPE_CHECKING:
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__)


class KmsLookup(LookupHandler):
    """AWS KMS lookup."""

    DEPRECATION_MSG = (
        'lookup query syntax "<region>@<encrypted-blob>" has been deprecated; '
        "to learn how to use the new lookup query syntax visit "
        f"{DOC_SITE}/page/cfngin/lookups/kms.html"
    )
    TYPE_NAME: Final[Literal["kms"]] = "kms"
    """Name that the Lookup is registered as."""

    @classmethod
    def legacy_parse(cls, value: str) -> Tuple[str, Dict[str, str]]:
        """Retain support for legacy lookup syntax.

        Format of value::

            <region>@<encrypted-blob>

        """
        LOGGER.warning("${%s %s}: %s", cls.TYPE_NAME, value, cls.DEPRECATION_MSG)
        region, value = read_value_from_path(value).split("@", 1)
        return value, {"region": region}

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, **_: Any
    ) -> str:
        r"""Decrypt the specified value with a master key in KMS.

        Args:
            value: Parameter(s) given to this lookup.
            context: Context instance.

        """
        if "@" in value:
            query, args = cls.legacy_parse(value)
        else:
            query, args = cls.parse(value)

        kms = context.get_session(region=args.get("region")).client("kms")

        decrypted = cast(
            Union[BinaryIO, bytes],
            kms.decrypt(CiphertextBlob=codecs.decode(query.encode(), "base64")).get(
                "Plaintext", b""
            ),
        )
        if isinstance(decrypted, bytes):
            return cls.format_results(decrypted.decode(), **args)
        return cls.format_results(decrypted.read().decode(), **args)
