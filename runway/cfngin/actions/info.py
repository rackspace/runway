"""CFNgin info action."""
import logging

from .. import exceptions
from .base import BaseAction

LOGGER = logging.getLogger(__name__)


class Action(BaseAction):  # pylint: disable=abstract-method
    """Get information on CloudFormation stacks.

    Displays the outputs for the set of CloudFormation stacks.

    """

    NAME = "info"

    def run(self, **kwargs):
        """Get information on CloudFormation stacks."""
        LOGGER.info("outputs for stacks: %s", self.context.get_fqn())
        if not self.context.get_stacks():
            LOGGER.warning("no stacks detected (error in config?)")
        for stack in self.context.get_stacks():
            provider = self.build_provider(stack)

            try:
                provider_stack = provider.get_stack(stack.fqn)
            except exceptions.StackDoesNotExist:
                LOGGER.info(
                    "%s:stack does not exist", stack.fqn,
                )
                continue

            LOGGER.info("%s:", stack.fqn)
            if "Outputs" in provider_stack:
                for output in provider_stack["Outputs"]:
                    LOGGER.info("\t%s: %s", output["OutputKey"], output["OutputValue"])
