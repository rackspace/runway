"""CFNgin lookup registry."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Type, Union

from ...lookups.handlers import cfn, ecr, ssm
from ...util import DOC_SITE, load_object_from_string
from .handlers import ami, default, dynamodb, envvar
from .handlers import file as file_handler
from .handlers import hook_data, kms, output, rxref, split, ssmstore, xref

if TYPE_CHECKING:
    from ...lookups.handlers.base import LookupHandler

CFNGIN_LOOKUP_HANDLERS: Dict[str, Union[Callable[..., Any], Type[LookupHandler]]] = {}
LOGGER = logging.getLogger(__name__)


def register_lookup_handler(
    lookup_type: str,
    handler_or_path: Union[Callable[..., Any], str, Type[LookupHandler]],
) -> None:
    """Register a lookup handler.

    Args:
        lookup_type: Name to register the handler under.
        handler_or_path: A function or a path to a handler.

    """
    handler = handler_or_path
    LOGGER.debug("registering CFNgin lookup: %s=%s", lookup_type, handler_or_path)

    if isinstance(handler_or_path, str):
        handler = load_object_from_string(handler_or_path)
    else:
        handler = handler_or_path

    if not isinstance(handler, type):
        # Hander is a not a new-style handler
        LOGGER.warning(
            'lookup "%s" uses a deprecated format; to learn how to write '
            "lookups visit %s/page/cfngin/lookups.html#writing-a-custom-lookup",
            lookup_type,
            DOC_SITE,
        )
    CFNGIN_LOOKUP_HANDLERS[lookup_type] = handler


def unregister_lookup_handler(lookup_type: str) -> None:
    """Unregister the specified lookup type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        lookup_type: Name of the lookup type to unregister.

    """
    CFNGIN_LOOKUP_HANDLERS.pop(lookup_type, None)


register_lookup_handler(ami.TYPE_NAME, ami.AmiLookup)
register_lookup_handler(cfn.TYPE_NAME, cfn.CfnLookup)
register_lookup_handler(default.TYPE_NAME, default.DefaultLookup)
register_lookup_handler(dynamodb.TYPE_NAME, dynamodb.DynamodbLookup)
register_lookup_handler(ecr.TYPE_NAME, ecr.EcrLookup)
register_lookup_handler(envvar.TYPE_NAME, envvar.EnvvarLookup)
register_lookup_handler(file_handler.TYPE_NAME, file_handler.FileLookup)
register_lookup_handler(hook_data.TYPE_NAME, hook_data.HookDataLookup)
register_lookup_handler(kms.TYPE_NAME, kms.KmsLookup)
register_lookup_handler(output.TYPE_NAME, output.OutputLookup)
register_lookup_handler(rxref.TYPE_NAME, rxref.RxrefLookup)
register_lookup_handler(split.TYPE_NAME, split.SplitLookup)
register_lookup_handler(ssm.TYPE_NAME, ssm.SsmLookup)
register_lookup_handler(ssmstore.TYPE_NAME, ssmstore.SsmstoreLookup)
register_lookup_handler(xref.TYPE_NAME, xref.XrefLookup)
