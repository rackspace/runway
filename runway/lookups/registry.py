"""Register test handlers."""
from typing import Type, Union  # pylint: disable=unused-import

from six import string_types

from runway.util import load_object_from_string

from .handlers import cfn, env, ssm, var
from .handlers.base import LookupHandler  # noqa: F401 pylint: disable=W

RUNWAY_LOOKUP_HANDLERS = {}


def register_lookup_handler(lookup_type, handler_or_path):
    # type: (str, Union[Type[LookupHandler], str]) -> None
    """Register a lookup handler.

    Args:
        lookup_type: Name to register the handler under
        handler_or_path: a function or a path to a handler

    """
    handler = handler_or_path
    if isinstance(handler_or_path, string_types):
        handler = load_object_from_string(handler_or_path)
    RUNWAY_LOOKUP_HANDLERS[lookup_type] = handler


def unregister_lookup_handler(lookup_type):
    # type: (str) -> None
    """Unregister the specified test type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        lookup_type: Name of the lookup type to unregister

    """
    RUNWAY_LOOKUP_HANDLERS.pop(lookup_type, None)


register_lookup_handler(cfn.TYPE_NAME, cfn.CfnLookup)
register_lookup_handler(env.TYPE_NAME, env.EnvLookup)
register_lookup_handler(ssm.TYPE_NAME, ssm.SsmLookup)
register_lookup_handler(var.TYPE_NAME, var.VarLookup)
