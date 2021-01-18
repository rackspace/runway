"""Handler for fetching outputs from a stack in the current namespace."""
# pylint: disable=arguments-differ,unused-argument
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ....lookups.handlers.base import LookupHandler
from .output import deconstruct

if TYPE_CHECKING:
    from ...context import Context
    from ...providers.aws.default import Provider

TYPE_NAME = "rxref"


class RxrefLookup(LookupHandler):
    """Rxref lookup."""

    @classmethod
    def handle(
        cls,
        value: str,
        context: Optional[Context] = None,
        provider: Optional[Provider] = None,
        **_: Any
    ) -> str:
        """Fetch an output from the designated stack in the current namespace.

        The ``output`` lookup supports fetching outputs from stacks created
        within a single config file. Sometimes it's useful to fetch outputs
        from stacks created outside of the current config file but using the
        same namespace. ``rxref`` supports this by using the
        :class:`runway.cfngin.context.Context` to expand the fqn of the stack.

        Args:
            value: Parameter(s) given to this lookup. `<stack_name>::<output_name>``
            context: Context instance.
            provider: Provider instance.

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
        return provider.get_output(stack_fqn, decon.output_name)
