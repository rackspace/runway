"""Handler for fetching outputs from a stack in the current namespace."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....lookups.handlers.base import LookupHandler
from .output import deconstruct

if TYPE_CHECKING:
    from ....context import CfnginContext
    from ...providers.aws.default import Provider

TYPE_NAME = "rxref"


class RxrefLookup(LookupHandler):
    """Rxref lookup."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, provider: Provider, **_: Any
    ) -> str:
        """Fetch an output from the designated stack in the current namespace.

        The ``output`` lookup supports fetching outputs from stacks created
        within a single config file. Sometimes it's useful to fetch outputs
        from stacks created outside of the current config file but using the
        same namespace. ``rxref`` supports this by using the
        :class:`runway.context.CfnginContext` to expand the fqn of the stack.

        Args:
            value: Parameter(s) given to this lookup. `<stack_name>::<output_name>``
            context: Context instance.
            provider: Provider instance.

        Example:
            ::

                conf_value: ${rxref relative-stack-name::SomeOutputName}

        """
        decon = deconstruct(value)
        stack_fqn = context.get_fqn(decon.stack_name)
        return provider.get_output(stack_fqn, decon.output_name)
