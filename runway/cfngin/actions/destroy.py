"""CFNgin destroy action."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from ..exceptions import StackDoesNotExist
from ..hooks.utils import handle_hooks
from ..status import (
    INTERRUPTED,
    PENDING,
    SUBMITTED,
    CompleteStatus,
    DoesNotExistInCloudFormation,
    FailedStatus,
    SubmittedStatus,
)
from .base import STACK_POLL_TIME, BaseAction, build_walker

if TYPE_CHECKING:
    from ..stack import Stack
    from ..status import Status

LOGGER = logging.getLogger(__name__)

DESTROYED_STATUS = CompleteStatus("stack destroyed")
DESTROYING_STATUS = SubmittedStatus("submitted for destruction")


class Action(BaseAction):
    """Responsible for destroying CloudFormation stacks.

    Generates a destruction plan based on stack dependencies. Stack
    dependencies are reversed from the deploy action. For example, if a Stack B
    requires Stack A during deploy, during destroy Stack A requires Stack B be
    destroyed first.

    The plan defaults to printing an outline of what will be destroyed. If
    forced to execute, each stack will get destroyed in order.

    """

    DESCRIPTION = "Destroy stacks"
    NAME = "destroy"

    @property
    def _stack_action(self) -> Callable[..., Status]:
        """Run against a step."""
        return self._destroy_stack

    def _destroy_stack(
        self, stack: Stack, *, status: Optional[Status], **_: Any
    ) -> Status:
        wait_time = 0 if status is PENDING else STACK_POLL_TIME
        if self.cancel.wait(wait_time):
            return INTERRUPTED

        provider = self.build_provider()

        try:
            stack_data = provider.get_stack(stack.fqn)
        except StackDoesNotExist:
            LOGGER.debug("%s:stack does not exist", stack.fqn)
            # Once the stack has been destroyed, it doesn't exist. If the
            # status of the step was SUBMITTED, we know we just deleted it,
            # otherwise it should be skipped
            if status == SUBMITTED:
                return DESTROYED_STATUS
            return DoesNotExistInCloudFormation()

        LOGGER.debug(
            "%s:provider status: %s",
            provider.get_stack_name(stack_data),
            provider.get_stack_status(stack_data),
        )
        if provider.is_stack_destroyed(stack_data):
            return DESTROYED_STATUS
        if provider.is_stack_in_progress(stack_data):
            return DESTROYING_STATUS
        if provider.is_stack_destroy_possible(stack_data):
            LOGGER.debug("%s:destroying stack", stack.fqn)
            provider.destroy_stack(stack_data)
            return DESTROYING_STATUS
        LOGGER.critical(
            "%s: %s", stack.fqn, provider.get_delete_failed_status_reason(stack.fqn)
        )
        return FailedStatus(provider.get_stack_status_reason(stack_data))

    def pre_run(
        self,
        *,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        outline: bool = False,
        **__kwargs: Any,
    ) -> None:
        """Any steps that need to be taken prior to running the action."""
        pre_destroy = self.context.config.pre_destroy
        if not outline and pre_destroy:
            handle_hooks(
                stage="pre_destroy",
                hooks=pre_destroy,
                provider=self.provider,
                context=self.context,
            )

    def run(
        self,
        *,
        concurrency: int = 0,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        force: bool = False,
        outline: bool = False,  # pylint: disable=unused-argument
        tail: bool = False,
        upload_disabled: bool = False,  # pylint: disable=unused-argument
        **_kwargs: Any,
    ) -> None:
        """Kicks off the destruction of the stacks in the stack_definitions."""
        plan = self._generate_plan(
            tail=tail, reverse=True, include_persistent_graph=True
        )
        if not plan.keys():
            LOGGER.warning("no stacks detected (error in config?)")
        if force:
            # need to generate a new plan to log since the outline sets the
            # steps to COMPLETE in order to log them
            plan.outline(logging.DEBUG)
            self.context.lock_persistent_graph(plan.lock_code)
            walker = build_walker(concurrency)
            try:
                plan.execute(walker)
            finally:
                self.context.unlock_persistent_graph(plan.lock_code)
        else:
            plan.outline(message='To execute this plan, run with --force" flag.')

    def post_run(
        self,
        *,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        outline: bool = False,
        **__kwargs: Any,
    ) -> None:
        """Any steps that need to be taken after running the action."""
        if not outline and self.context.config.post_destroy:
            handle_hooks(
                stage="post_destroy",
                hooks=self.context.config.post_destroy,
                provider=self.provider,
                context=self.context,
            )
