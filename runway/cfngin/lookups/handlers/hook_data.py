"""Hook data lookup."""
# pylint: disable=arguments-differ,unused-argument
from runway.lookups.handlers.base import LookupHandler

TYPE_NAME = "hook_data"


class HookDataLookup(LookupHandler):
    """Hook data lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Return the value of a key for a given hook in hook_data.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Format of value:

            <hook_name>::<key>

        """
        try:
            hook_name, key = value.split("::")
        except ValueError:
            raise ValueError("Invalid value for hook_data: %s. Must be in "
                             "<hook_name>::<key> format." % value)

        return context.hook_data[hook_name][key]
