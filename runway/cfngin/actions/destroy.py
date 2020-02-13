"""CFNgin destroy action."""
import logging

from ..exceptions import StackDoesNotExist
from ..hooks.utils import handle_hooks
from ..status import INTERRUPTED, PENDING, SUBMITTED, CompleteStatus
from ..status import StackDoesNotExist as StackDoesNotExistStatus
from ..status import SubmittedStatus
from .base import STACK_POLL_TIME, BaseAction, build_walker

LOGGER = logging.getLogger(__name__)

DESTROYED_STATUS = CompleteStatus("stack destroyed")
DESTROYING_STATUS = SubmittedStatus("submitted for destruction")


class Action(BaseAction):
    """Responsible for destroying CloudFormation stacks.

    Generates a destruction plan based on stack dependencies. Stack
    dependencies are reversed from the build action. For example, if a Stack B
    requires Stack A during build, during destroy Stack A requires Stack B be
    destroyed first.

    The plan defaults to printing an outline of what will be destroyed. If
    forced to execute, each stack will get destroyed in order.

    """

    DESCRIPTION = 'Destroy stacks'

    @property
    def _stack_action(self):
        """Run against a step."""
        return self._destroy_stack

    def _destroy_stack(self, stack, **kwargs):
        old_status = kwargs.get("status")
        wait_time = 0 if old_status is PENDING else STACK_POLL_TIME
        if self.cancel.wait(wait_time):
            return INTERRUPTED

        provider = self.build_provider(stack)

        try:
            provider_stack = provider.get_stack(stack.fqn)
        except StackDoesNotExist:
            LOGGER.debug("Stack %s does not exist.", stack.fqn)
            # Once the stack has been destroyed, it doesn't exist. If the
            # status of the step was SUBMITTED, we know we just deleted it,
            # otherwise it should be skipped
            if kwargs.get("status", None) == SUBMITTED:
                return DESTROYED_STATUS
            return StackDoesNotExistStatus()

        LOGGER.debug(
            "Stack %s provider status: %s",
            provider.get_stack_name(provider_stack),
            provider.get_stack_status(provider_stack),
        )
        if provider.is_stack_destroyed(provider_stack):
            return DESTROYED_STATUS
        if provider.is_stack_in_progress(provider_stack):
            return DESTROYING_STATUS
        LOGGER.debug("Destroying stack: %s", stack.fqn)
        provider.destroy_stack(provider_stack)
        return DESTROYING_STATUS

    def pre_run(self, **kwargs):
        """Any steps that need to be taken prior to running the action."""
        pre_destroy = self.context.config.pre_destroy
        if not kwargs.get('outline') and pre_destroy:
            handle_hooks(
                stage="pre_destroy",
                hooks=pre_destroy,
                provider=self.provider,
                context=self.context)

    def run(self, **kwargs):
        """Kicks off the destruction of the stacks in the stack_definitions."""
        plan = self._generate_plan(tail=kwargs.get('tail'), reverse=True,
                                   include_persistent_graph=True)
        if not plan.keys():
            LOGGER.warning('WARNING: No stacks detected (error in config?)')
        if kwargs.get('force', False):
            # need to generate a new plan to log since the outline sets the
            # steps to COMPLETE in order to log them
            plan.outline(logging.DEBUG)
            self.context.lock_persistent_graph(plan.lock_code)
            walker = build_walker(kwargs.get('concurrency', 0))
            try:
                plan.execute(walker)
            finally:
                self.context.unlock_persistent_graph(plan.lock_code)
        else:
            plan.outline(message="To execute this plan, run with "
                                 "\"--force\" flag.")

    def post_run(self, **kwargs):
        """Any steps that need to be taken after running the action."""
        post_destroy = self.context.config.post_destroy
        if not kwargs.get('outline') and post_destroy:
            handle_hooks(
                stage="post_destroy",
                hooks=post_destroy,
                provider=self.provider,
                context=self.context)
