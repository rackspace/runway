"""Handler for fetching outputs from fully qualified stacks."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ....lookups.handlers.base import LookupHandler
from .output import deconstruct

if TYPE_CHECKING:
    from ...providers.aws.default import Provider

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "xref"

XREF_PRESISTENT_STATE = {"has_warned": False}


class XrefLookup(LookupHandler):
    """Xref lookup."""

    DEPRECATION_MSG = "xref Lookup has been deprecated; use the cfn lookup instead"

    @classmethod
    def handle(  # pylint: disable=arguments-differ,arguments-renamed
        cls, value: str, provider: Provider, **_: Any
    ) -> str:
        """Fetch an output from the designated, fully qualified stack.

        The `output` handler supports fetching outputs from stacks created
        within a single config file. Sometimes it's useful to fetch outputs
        from stacks created outside of the current config file. `xref`
        supports this by **not** using the
        :class:`runway.context.CfnginContext` to expand the fqn of the stack.

        Args:
            value: Parameter(s) given to this lookup. ``<stack_name>::<output_name>``
            provider: Provider instance.

        Returns:
            Output from the specified stack.

        Example:
            ::

                conf_value: ${xref fully-qualified-stack-name::SomeOutputName}

        """
        decon = deconstruct(value)
        stack_fqn = decon.stack_name
        return provider.get_output(stack_fqn, decon.output_name)
