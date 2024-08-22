"""Split lookup."""

from typing import Any, ClassVar

from ....lookups.handlers.base import LookupHandler


class SplitLookup(LookupHandler[Any]):
    """Split lookup."""

    TYPE_NAME: ClassVar[str] = "split"
    """Name that the Lookup is registered as."""

    @classmethod
    def handle(cls, value: str, *_args: Any, **_kwargs: Any) -> list[str]:
        """Split the supplied string on the given delimiter, providing a list.

        Args:
            value: Parameter(s) given to this lookup.

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

                Subnets: ${split ,::${output vpc.PrivateSubnets}}

        """
        try:
            delimiter, text = value.split("::", 1)
        except ValueError:
            raise ValueError(
                f"Invalid value for split: {value}. Must be in <delimiter>::<text> format."
            ) from None

        return text.split(delimiter)
