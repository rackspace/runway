"""CFNgin lookup base class."""


class LookupHandler(object):
    """Lookup base class."""

    @classmethod
    def handle(cls, value, context=None, provider=None):
        """Perform the lookup.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Looked up value

        """
        raise NotImplementedError

    @classmethod
    def dependencies(cls, lookup_data):
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_data may not be (completely) resolved at this time.

        Args:
            lookup_data (:class`runway.cfngin.variables.VariableValue`):
                Parameter(s) given to this lookup.

        Returns:
            Set[str]: Stack names this lookup depends on.

        """
        del lookup_data  # unused in this implementation
        return set()
