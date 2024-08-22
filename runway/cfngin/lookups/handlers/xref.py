"""Handler for fetching outputs from fully qualified stacks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from ....lookups.handlers.base import LookupHandler
from .output import deconstruct

if TYPE_CHECKING:

    from ...providers.aws.default import Provider

LOGGER = logging.getLogger(__name__)

XREF_PERSISTENT_STATE = {"has_warned": False}


class XrefLookup(LookupHandler[Any]):
    """Xref lookup."""

    DEPRECATION_MSG = "xref Lookup has been deprecated; use the cfn lookup instead"
    TYPE_NAME: ClassVar[str] = "xref"
    """Name that the Lookup is registered as."""

    @classmethod
    def handle(cls, value: str, *_args: Any, provider: Provider, **_kwargs: Any) -> str:
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
