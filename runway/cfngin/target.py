"""CFNgin target."""


class Target(object):  # pylint: disable=too-few-public-methods
    """A "target" is just a node in the graph that only specify dependencies.

    These can be useful as a means of logically grouping a set of stacks
    together that can be targeted with the ``targets`` option.

    Attributes:
        logging (bool): Whether logging is enabled.
        name (str): Name of the target (stack) taken from the definition.
        required_by (List[str]): List of target (stack) names that depend on
            this stack.
        requires (List[str]): List of target (stack) names this target (stack)
            depends on.

    """

    def __init__(self, definition):
        """Instantiate class.

        Args:
            definition (:class:`runway.cfngin.config.Stack`): Stack definition
                for the target.

        """
        self.name = definition.name
        self.requires = definition.requires or []
        self.required_by = definition.required_by or []
        self.logging = False
