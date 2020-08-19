"""Handler for fetching outputs from a stack in the current namespace."""
# pylint: disable=arguments-differ,unused-argument
from runway.lookups.handlers.base import LookupHandler

from .output import deconstruct

TYPE_NAME = "rxref"


class RxrefLookup(LookupHandler):
    """Rxref lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Fetch an output from the designated stack in the current namespace.

        The ``output`` lookup supports fetching outputs from stacks created
        within a single config file. Sometimes it's useful to fetch outputs
        from stacks created outside of the current config file but using the
        same namespace. ``rxref`` supports this by using the
        :class:`runway.cfngin.context.Context` to expand the fqn of the stack.

        Args:
            value (str): Parameter(s) given to this lookup.
                ``<stack_name>::<output_name>``
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Output from the specified stack.

        Example:
            ::

                conf_value: ${rxref relative-stack-name::SomeOutputName}

        """
        if provider is None:
            raise ValueError("Provider is required")
        if context is None:
            raise ValueError("Context is required")

        decon = deconstruct(value)
        stack_fqn = context.get_fqn(decon.stack_name)
        output = provider.get_output(stack_fqn, decon.output_name)
        return output
