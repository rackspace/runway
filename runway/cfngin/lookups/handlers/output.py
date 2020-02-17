"""AWS CloudFormation Output lookup."""
# pylint: disable=arguments-differ,unused-argument
import re
from collections import namedtuple

from runway.lookups.handlers.base import LookupHandler

TYPE_NAME = "output"

Output = namedtuple("Output", ("stack_name", "output_name"))


class OutputLookup(LookupHandler):
    """AWS CloudFormation Output lookup."""

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
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
        if context is None:
            raise ValueError('Context is required')

        decon = deconstruct(value)
        stack = context.get_stack(decon.stack_name)
        return stack.outputs[decon.output_name]

    @classmethod
    def dependencies(cls, lookup_data):
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_data may not be (completely) resolved at this time.

        Args:
            lookup_data (VariableValue): Parameter(s) given to this lookup.

        Returns:
            Set[str]: Stack names this lookup depends on.

        """
        # try to get the stack name
        stack_name = ''
        for data_item in lookup_data:
            if not data_item.resolved:
                # We encountered an unresolved substitution.
                # StackName is calculated dynamically based on context:
                #  e.g. ${output ${default var::source}::name}
                # Stop here
                return set()
            stack_name = stack_name + data_item.value
            match = re.search(r'::', stack_name)
            if match:
                stack_name = stack_name[0:match.start()]
                return {stack_name}
            # else: try to append the next item

        # We added all lookup_data, and still couldn't find a `::`...
        # Probably an error...
        return set()


def deconstruct(value):
    """Deconstruct the value."""
    try:
        stack_name, output_name = value.split("::")
    except ValueError:
        raise ValueError("output handler requires syntax "
                         "of <stack>::<output>.  Got: %s" % value)

    return Output(stack_name, output_name)
