"""Base class for lookup handlers."""
from typing import Any, Optional, Set, TYPE_CHECKING  # noqa

if TYPE_CHECKING:
    from ...context import Context  # noqa


class LookupHandler(object):
    """Base class for lookup handlers."""

    @classmethod
    def dependencies(cls, lookup_data):
        # type: (Any) -> Set
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_data may not be (completely) resolved at this time.

        Args:
            lookup_data: The lookup data.

        """
        del lookup_data  # unused in this implementation
        return set()

    @classmethod
    def handle(cls, value, context, provider=None):
        # type: (str, 'Context', Optional[Any])
        """Perform the lookup.

        Args:
            value: Parameter(s) given to the lookup.
            context: The current context object.
            provider: Optional provider to use when handling the lookup.

        Returns:
            (Any) Looked-up value.

        """
        raise NotImplementedError
