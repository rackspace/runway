"""AWS CloudFormation Output lookup."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from ....exceptions import OutputDoesNotExist
from ....lookups.handlers.base import LookupHandler
from ....utils import DOC_SITE
from ...exceptions import StackDoesNotExist

if TYPE_CHECKING:

    from ....context import CfnginContext
    from ....lookups.handlers.base import ParsedArgsTypeDef
    from ....variables import VariableValue

LOGGER = logging.getLogger(__name__)


class OutputQuery(NamedTuple):
    """Output query NamedTuple."""

    stack_name: str
    output_name: str


class OutputLookup(LookupHandler["CfnginContext"]):
    """AWS CloudFormation Output lookup."""

    DEPRECATION_MSG = (
        'lookup query syntax "<relative-stack-name>::<OutputName>" has been deprecated; '
        "to learn how to use the new lookup query syntax visit "
        f"{DOC_SITE}/page/cfngin/lookups/output.html"
    )
    TYPE_NAME: ClassVar[str] = "output"
    """Name that the Lookup is registered as."""

    @classmethod
    def legacy_parse(cls, value: str) -> tuple[OutputQuery, ParsedArgsTypeDef]:
        """Retain support for legacy lookup syntax.

        Format of value:
            <relative-stack-name>::<OutputName>

        """
        LOGGER.warning("${%s %s}: %s", cls.TYPE_NAME, value, cls.DEPRECATION_MSG)
        return deconstruct(value), {}

    @classmethod
    def handle(cls, value: str, context: CfnginContext, **_: Any) -> str:
        """Fetch an output from the designated stack.

        Args:
            value: Parameter(s) given to this lookup.
                ``<relative-stack-name>.<OutputName>``
            context: Context instance.

        Returns:
            Output from the specified stack.

        Raises:
            OutputDoesNotExist: Output not found for Stack.
            StackDoesNotExist: Stack not found for the name provided.

        """
        try:
            raw_query, args = cls.parse(value)
            query = OutputQuery(*raw_query.split("."))
        except ValueError:
            query, args = cls.legacy_parse(value)

        stack = context.get_stack(query.stack_name)
        if not stack:
            if "default" in args:
                return cls.format_results(args["default"], **args)
            raise StackDoesNotExist(context.get_fqn(query.stack_name))

        if "default" in args:  # handle falsy default
            return cls.format_results(stack.outputs.get(query.output_name, args["default"]), **args)

        try:
            return cls.format_results(stack.outputs[query.output_name], **args)
        except KeyError:
            raise OutputDoesNotExist(
                stack_name=context.get_fqn(query.stack_name), output=query.output_name
            ) from None

    @classmethod
    def dependencies(cls, lookup_query: VariableValue) -> set[str]:
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
                #  e.g. ${output ${default var::source}.name}
                # Stop here
                return set()
            stack_name += data_item.value
            match = re.search(r"(::|\.)", stack_name)
            if match:
                stack_name = stack_name[0 : match.start()]
                return {stack_name}
                # else: try to append the next item

        # We added all lookup_query, and still couldn't find a `::`...
        # Probably an error...
        return set()


def deconstruct(value: str) -> OutputQuery:  # TODO (kyle): remove in next major release
    """Deconstruct the value."""
    try:
        stack_name, output_name = value.split("::")
    except ValueError:
        raise ValueError(
            f"output handler requires syntax of <stack>::<output>. Got: {value}"
        ) from None

    return OutputQuery(stack_name, output_name)
