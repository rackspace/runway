"""Handler for fetching outputs from fully qualified stacks.

The `output` handler supports fetching outputs from stacks created within a
single config file. Sometimes it's useful to fetch outputs from stacks created
outside of the current config file. `xref` supports this by not using the
:class:`runway.cfngin.context.Context` to expand the fqn of the stack.

Example::

    conf_value: ${xref some-fully-qualified-stack-name::SomeOutputName}

"""
# pylint: disable=unused-argument
from . import LookupHandler
from .output import deconstruct

TYPE_NAME = "xref"


class XrefLookup(LookupHandler):
    """Xref lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None):
        """Fetch an output from the designated stack.

        Args:
            value (str): Parameter(s) given to this lookup.
                ``<stack_name>::<output_name>``
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Output from the specified stack.

        """
        if provider is None:
            raise ValueError('Provider is required')

        decon = deconstruct(value)
        stack_fqn = decon.stack_name
        output = provider.get_output(stack_fqn, decon.output_name)
        return output
