"""AWS CloudFormation Output lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NamedTuple, Set

from ....lookups.handlers.base import LookupHandler
from ...exceptions import StackDoesNotExist

if TYPE_CHECKING:
    from ....context import CfnginContext
    from ....variables import VariableValue

TYPE_NAME = "output"


class OutputQuery(NamedTuple):
    """Output query NamedTuple."""

    stack_name: str
    output_name: str


class OutputLookup(LookupHandler):
    """AWS CloudFormation Output lookup."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, **_: Any
    ) -> str:
        """Fetch an output from the designated stack.

        Args:
            value: Parameter(s) given to this lookup.
                ``<stack_name>::<output_name>``
            context: Context instance.

        Returns:
            Output from the specified stack.

        Raises:
            StackDoesNotExist: Stack not found for the name provided.

        """
        decon = deconstruct(value)
        stack = context.get_stack(decon.stack_name)
        if stack:
            return stack.outputs[decon.output_name]
        raise StackDoesNotExist(context.get_fqn(decon.stack_name))

    @classmethod
    def dependencies(cls, lookup_query: VariableValue) -> Set[str]:
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_query may not be (completely) resolved at this time.

        Args:
            lookup_query: Parameter(s) given to this lookup.

        Returns:
            Stack names this lookup depends on.

        """
        # try to get the stack name
        stack_name = ""
        for data_item in lookup_query:
            if not data_item.resolved:
                # We encountered an unresolved substitution.
                # StackName is calculated dynamically based on context:
                #  e.g. ${output ${default var::source}::name}
                # Stop here
                return set()
            stack_name += data_item.value
            match = re.search(r"::", stack_name)
            if match:
                stack_name = stack_name[0 : match.start()]
                return {stack_name}
                # else: try to append the next item

        # We added all lookup_query, and still couldn't find a `::`...
        # Probably an error...
        return set()


def deconstruct(value: str) -> OutputQuery:
    """Deconstruct the value."""
    try:
        stack_name, output_name = value.split("::")
    except ValueError:
        raise ValueError(
            f"output handler requires syntax of <stack>::<output>. Got: {value}"
        ) from None

    return OutputQuery(stack_name, output_name)
