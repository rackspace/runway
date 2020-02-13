"""Split lookup."""
# pylint: disable=arguments-differ,unused-argument
from runway.lookups.handlers.base import LookupHandler

TYPE_NAME = "split"


class SplitLookup(LookupHandler):
    """Split lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Split the supplied string on the given delimiter, providing a list.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Looked up value.

        Format of value::

            <delimiter>::<value>

        Example:
            ::

                Subnets: ${split ,::subnet-1,subnet-2,subnet-3}

            Would result in the variable `Subnets` getting a list consisting
            of::

                ["subnet-1", "subnet-2", "subnet-3"]

            This is particularly useful when getting an output from another
            stack that contains a list. For example, the standard vpc blueprint
            outputs the list of Subnets it creates as a pair of Outputs
            (``PublicSubnets``, ``PrivateSubnets``) that are comma separated,
            so you could use this in your config::

                Subnets: ${split ,::${output vpc::PrivateSubnets}}

        """
        try:
            delimiter, text = value.split("::", 1)
        except ValueError:
            raise ValueError("Invalid value for split: %s. Must be in "
                             "<delimiter>::<text> format." % value)

        return text.split(delimiter)
