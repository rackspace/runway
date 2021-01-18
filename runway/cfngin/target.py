"""CFNgin target."""
from __future__ import annotations

from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from ..config.models.cfngin import CfnginTargetDefinitionModel


class Target:
    """A "target" is just a node in the graph that only specify dependencies.

    These can be useful as a means of logically grouping a set of stacks
    together that can be targeted with the ``targets`` option.

    Attributes:
        logging: Whether logging is enabled.
        name: Name of the target (stack) taken from the definition.
        required_by: List of target (stack) names that depend on
            this stack.
        requires: List of target (stack) names this target (stack) depends on.

    """

    logging: bool
    name: str
    required_by: Set[str]
    requires: Set[str]

    def __init__(self, definition: CfnginTargetDefinitionModel) -> None:
        """Instantiate class.

        Args:
            definition: Target definition.

        """
        self.name = definition.name
        self.requires = set(definition.requires or [])
        self.required_by = set(definition.required_by or [])
        self.logging = False
