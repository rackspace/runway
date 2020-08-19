"""Hook data lookup."""
# pylint: disable=arguments-differ,unused-argument
import logging
import warnings

from troposphere import BaseAWSObject

from runway.lookups.handlers.base import LookupHandler
from runway.util import DOC_SITE, MutableMap  # abs to support import through shim

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "hook_data"


class HookDataLookup(LookupHandler):
    """Hook data lookup."""

    DEPRECATION_MSG = (
        'lookup query syntax "<hook_name>::<key>" has been deprecated; to '
        "learn how to use the new lookup query syntax visit "
        "{}/page/lookups.html".format(DOC_SITE)
    )

    @classmethod
    def legacy_parse(cls, value):
        """Retain support for legacy lookup syntax.

        Args:
            value (str): Parameter(s) given to this lookup.

        Format of value:
            <hook_name>::<key>

        """
        hook_name, key = value.split("::")
        warnings.warn(cls.DEPRECATION_MSG, DeprecationWarning)
        LOGGER.warning(cls.DEPRECATION_MSG)
        return "{}.{}".format(hook_name, key), {}

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Return the data from ``hook_data``.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        """
        try:
            query, args = cls.parse(value)
        except ValueError:
            query, args = cls.legacy_parse(value)

        hook_data = MutableMap(**context.hook_data)

        # TODO use context.hook_data directly in next major release
        result = hook_data.find(query, args.get("default"))

        if (
            isinstance(result, BaseAWSObject)
            and args.get("get")
            and not args.get("load")
        ):
            args["load"] = "troposphere"

        if not result:
            raise ValueError('Could not find a value for "%s"' % value)

        if result == args.get("default"):
            # assume default value has already been processed so no need to
            # use these
            args.pop("load", None)
            args.pop("get", None)

        return cls.format_results(result, **args)
