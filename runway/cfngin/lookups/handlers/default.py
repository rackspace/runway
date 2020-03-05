"""Lookup to provide a default value."""
# pylint: disable=arguments-differ,unused-argument
from runway.lookups.handlers.base import LookupHandler


TYPE_NAME = "default"


class DefaultLookup(LookupHandler):
    """Lookup to provide a default value."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Use a value from the environment or fall back to a default value.

        Allows defaults to be set at the config file level.

        Args:
            value (str): Parameter(s) given to this lookup.
                ``<env_var>::<default value>``
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Looked up value

        Example:
            ::

                Groups: ${default app_security_groups::sg-12345,sg-67890}

            If ``app_security_groups`` is defined in the environment, its
            defined value will be returned. Otherwise, ``sg-12345,sg-67890``
            will be thereturned value.

        """
        try:
            env_var_name, default_val = value.split("::", 1)
        except ValueError:
            raise ValueError("Invalid value for default: %s. Must be in "
                             "<env_var>::<default value> format." % value)

        if env_var_name in context.environment:
            return context.environment[env_var_name]
        return default_val
