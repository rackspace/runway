"""CFNgin build action."""
import logging

from ..exceptions import (
    CancelExecution,
    MissingParameterException,
    StackDidNotChange,
    StackDoesNotExist,
)
from ..hooks import utils
from ..plan import Graph, Plan, Step
from ..providers.base import Template
from ..status import (
    COMPLETE,
    INTERRUPTED,
    PENDING,
    SUBMITTED,
    WAITING,
    CompleteStatus,
    DidNotChangeStatus,
    FailedStatus,
    NotSubmittedStatus,
    NotUpdatedStatus,
    SkippedStatus,
)
from ..status import StackDoesNotExist as StackDoesNotExistStatus
from ..status import SubmittedStatus
from .base import STACK_POLL_TIME, BaseAction, build_walker

LOGGER = logging.getLogger(__name__)

DESTROYED_STATUS = CompleteStatus("stack destroyed")
DESTROYING_STATUS = SubmittedStatus("submitted for destruction")


def build_stack_tags(stack):
    """Build a common set of tags to attach to a stack."""
    return [{"Key": t[0], "Value": t[1]} for t in stack.tags.items()]


def should_update(stack):
    """Test whether a stack should be submitted for updates to CloudFormation.

    Args:
        stack (:class:`runway.cfngin.stack.Stack`): The stack object to check.

    Returns:
        bool: If the stack should be updated, return True.

    """
    if stack.locked:
        if not stack.force:
            LOGGER.debug(
                "%s:locked and not in --force list; refusing to update", stack.name
            )
            return False
        LOGGER.debug("%s:locked but is in --force list", stack.name)
    return True


def should_submit(stack):
    """Test whether a stack should be submitted to CF for update/create.

    Args:
        stack (:class:`runway.cfngin.stack.Stack`): The stack object to check.

    Returns:
        bool: If the stack should be submitted, return True.

    """
    if stack.enabled:
        return True

    LOGGER.debug("%s:skipped; stack is not enabled", stack.name)
    return False


def should_ensure_cfn_bucket(outline, dump):
    """Test whether access to the cloudformation template bucket is required.

    Args:
        outline (bool): The outline action.
        dump (bool): The dump action.

    Returns:
        bool: If access to CF bucket is needed, return True.

    """
    return not outline and not dump


def _resolve_parameters(parameters, blueprint):
    """Resolve CloudFormation Parameters for a given blueprint.

    Given a list of parameters, handles:
        - discard any parameters that the blueprint does not use
        - discard any empty values
        - convert booleans to strings suitable for CloudFormation

    Args:
        parameters (dict): A dictionary of parameters provided by the
            stack definition
        blueprint (:class:`runway.cfngin.blueprint.base.Blueprint`):
            A Blueprint object that is having the parameters applied to it.

    Returns:
        dict: The resolved parameters.

    """
    params = {}
    param_defs = blueprint.get_parameter_definitions()

    for key, value in parameters.items():
        if key not in param_defs:
            LOGGER.debug("blueprint %s does not use parameter %s", blueprint.name, key)
            continue
        if value is None:
            LOGGER.debug(
                "got NoneType value for parameter %s; not submitting it "
                "to cloudformation, default value should be used",
                key,
            )
            continue
        if isinstance(value, bool):
            LOGGER.debug('converting parameter %s boolean "%s" to string', key, value)
            value = str(value).lower()
        params[key] = value
    return params


class UsePreviousParameterValue(object):  # pylint: disable=too-few-public-methods
    """Class used to indicate a Parameter should use it's existing value."""


def _handle_missing_parameters(
    parameter_values, all_params, required_params, existing_stack=None
):
    """Handle any missing parameters.

    If an existing_stack is provided, look up missing parameters there.

    Args:
        parameter_values (dict): key/value dictionary of stack definition
            parameters
        all_params (list): A list of all the parameters used by the
            template/blueprint.
        required_params (list): A list of all the parameters required by the
            template/blueprint.
        existing_stack (dict): A dict representation of the stack. If
            provided, will be searched for any missing parameters.

    Returns:
        list of tuples: The final list of key/value pairs returned as a
            list of tuples.

    Raises:
        MissingParameterException: Raised if a required parameter is
            still missing.

    """
    missing_params = list(set(all_params) - set(parameter_values.keys()))
    if existing_stack and "Parameters" in existing_stack:
        stack_parameters = [
            param["ParameterKey"] for param in existing_stack["Parameters"]
        ]
        for param in missing_params:
            if param in stack_parameters:
                LOGGER.debug(
                    "using previous value for parameter %s from existing stack", param,
                )
                parameter_values[param] = UsePreviousParameterValue
    final_missing = list(set(required_params) - set(parameter_values.keys()))
    if final_missing:
        raise MissingParameterException(final_missing)

    return list(parameter_values.items())


def handle_hooks(stage, hooks, provider, context, dump, outline):
    """Handle pre/post hooks.

    Args:
        stage (str): The name of the hook stage - pre_build/post_build.
        hooks (list): A list of dictionaries containing the hooks to execute.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): The provider
            the current stack is using.
        context (:class:`runway.cfngin.context.Context`): The current CFNgin
            context.
        dump (bool): Whether running with dump set or not.
        outline (bool): Whether running with outline set or not.

    """
    if not outline and not dump and hooks:
        utils.handle_hooks(stage=stage, hooks=hooks, provider=provider, context=context)


class Action(BaseAction):
    """Responsible for building & coordinating CloudFormation stacks.

    Generates the build plan based on stack dependencies (these dependencies
    are determined automatically based on output lookups from other stacks).

    The plan can then either be printed out as an outline or executed. If
    executed, each stack will get launched in order which entails:

    - Pushing the generated CloudFormation template to S3 if it has changed
    - Submitting either a build or update of the given stack to the
      :class:`runway.cfngin.providers.base.BaseProvider`.

    """

    DESCRIPTION = "Create/Update stacks"
    NAME = "build"

    @staticmethod
    def build_parameters(stack, provider_stack=None):
        """Build the CloudFormation Parameters for our stack.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): A CFNgin stack.
            provider_stack (Dict[str, Any]): An optional CFNgin provider object.

        Returns:
            Dict[str, Any]: The parameters for the given stack

        """
        resolved = _resolve_parameters(stack.parameter_values, stack.blueprint)
        required_parameters = list(stack.required_parameter_definitions)
        all_parameters = list(stack.all_parameter_definitions)
        parameters = _handle_missing_parameters(
            resolved, all_parameters, required_parameters, provider_stack
        )

        param_list = []

        for key, value in parameters:
            param_dict = {"ParameterKey": key}
            if value is UsePreviousParameterValue:
                param_dict["UsePreviousValue"] = True
            else:
                param_dict["ParameterValue"] = str(value)

            param_list.append(param_dict)

        return param_list

    def _destroy_stack(  # pylint: disable=too-many-return-statements
        self, stack, **kwargs
    ):
        """Delete a CloudFormation stack.

        Used to remove stacks that exist in the persistent graph but not
        have been removed from the "local" graph.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): Stack to be deleted.

        """
        stack_status = kwargs.get("status")
        wait_time = 0 if stack_status is PENDING else STACK_POLL_TIME
        if self.cancel.wait(wait_time):
            return INTERRUPTED

        provider = self.build_provider(stack)

        try:
            stack_data = provider.get_stack(stack.fqn)
        except StackDoesNotExist:
            LOGGER.debug("%s:stack does not exist", stack.fqn)
            if kwargs.get("status", None) == SUBMITTED:
                return DESTROYED_STATUS
            return StackDoesNotExistStatus()

        LOGGER.debug(
            "%s:provider status: %s",
            provider.get_stack_name(stack_data),
            provider.get_stack_status(stack_data),
        )
        try:
            if provider.is_stack_being_destroyed(stack_data):
                return DESTROYING_STATUS
            if provider.is_stack_destroyed(stack_data):
                return DESTROYED_STATUS
            wait = stack.in_progress_behavior == "wait"
            if wait and provider.is_stack_in_progress(stack_data):
                return WAITING
            LOGGER.debug("%s:destroying stack", stack.fqn)
            provider.destroy_stack(stack_data, action="build")
            return DESTROYING_STATUS
        except CancelExecution:
            return SkippedStatus(reason="canceled execution")

    # TODO refactor long if, elif, else block
    def _launch_stack(self, stack, **kwargs):  # pylint: disable=R
        """Handle the creating or updating of a stack in CloudFormation.

        Also makes sure that we don't try to create or update a stack while
        it is already updating or creating.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): Stack to be launched.

        """
        old_status = kwargs.get("status")
        wait_time = 0 if old_status is PENDING else STACK_POLL_TIME
        if self.cancel.wait(wait_time):
            return INTERRUPTED

        if not should_submit(stack):
            return NotSubmittedStatus()

        provider = self.build_provider(stack)

        try:
            provider_stack = provider.get_stack(stack.fqn)
        except StackDoesNotExist:
            provider_stack = None

        if provider_stack and not should_update(stack):
            stack.set_outputs(self.provider.get_output_dict(provider_stack))
            return NotUpdatedStatus()

        recreate = False
        if provider_stack and old_status == SUBMITTED:
            LOGGER.debug(
                "%s:provider status: %s",
                stack.fqn,
                provider.get_stack_status(provider_stack),
            )

            if provider.is_stack_rolling_back(  # pylint: disable=no-else-return
                provider_stack
            ):
                if "rolling back" in old_status.reason:
                    return old_status

                LOGGER.debug("%s:entered roll back", stack.fqn)
                if "updating" in old_status.reason:
                    reason = "rolling back update"
                else:
                    reason = "rolling back new stack"

                return SubmittedStatus(reason)
            elif provider.is_stack_in_progress(provider_stack):
                LOGGER.debug("%s:in progress", stack.fqn)
                return old_status
            elif provider.is_stack_destroyed(provider_stack):
                LOGGER.debug("%s:finished deleting", stack.fqn)
                recreate = True
                # Continue with creation afterwards
            # Failure must be checked *before* completion, as both will be true
            # when completing a rollback, and we don't want to consider it as
            # a successful update.
            elif provider.is_stack_failed(provider_stack):
                reason = old_status.reason
                if "rolling" in reason:
                    reason = reason.replace("rolling", "rolled")
                status_reason = provider.get_rollback_status_reason(stack.fqn)
                LOGGER.info("%s:roll back reason: %s", stack.fqn, status_reason)
                return FailedStatus(reason)

            elif provider.is_stack_completed(provider_stack):
                stack.set_outputs(provider.get_output_dict(provider_stack))
                return CompleteStatus(old_status.reason)
            else:
                return old_status

        LOGGER.debug("%s:resolving stack", stack.fqn)
        stack.resolve(self.context, self.provider)

        LOGGER.debug("%s:launching stack now", stack.fqn)
        template = self._template(stack.blueprint)
        stack_policy = self._stack_policy(stack)
        tags = build_stack_tags(stack)
        parameters = self.build_parameters(stack, provider_stack)
        force_change_set = stack.blueprint.requires_change_set

        if recreate:
            LOGGER.debug("%s:re-creating stack", stack.fqn)
            provider.create_stack(
                stack.fqn,
                template,
                parameters,
                tags,
                stack_policy=stack_policy,
                termination_protection=stack.termination_protection,
            )
            return SubmittedStatus("re-creating stack")
        if not provider_stack:
            LOGGER.debug("%s:creating new stack", stack.fqn)
            provider.create_stack(
                stack.fqn,
                template,
                parameters,
                tags,
                force_change_set,
                stack_policy=stack_policy,
                termination_protection=stack.termination_protection,
            )
            return SubmittedStatus("creating new stack")

        try:
            wait = stack.in_progress_behavior == "wait"
            if wait and provider.is_stack_in_progress(provider_stack):
                return WAITING
            if provider.prepare_stack_for_update(provider_stack, tags):
                existing_params = provider_stack.get("Parameters", [])
                provider.update_stack(
                    stack.fqn,
                    template,
                    existing_params,
                    parameters,
                    tags,
                    force_interactive=stack.protected,
                    force_change_set=force_change_set,
                    stack_policy=stack_policy,
                    termination_protection=stack.termination_protection,
                )

                LOGGER.debug("%s:updating existing stack", stack.fqn)
                return SubmittedStatus("updating existing stack")
            return SubmittedStatus("destroying stack for re-creation")
        except CancelExecution:
            stack.set_outputs(provider.get_output_dict(provider_stack))
            return SkippedStatus(reason="canceled execution")
        except StackDidNotChange:
            stack.set_outputs(provider.get_output_dict(provider_stack))
            return DidNotChangeStatus()

    @property
    def _stack_action(self):
        """Run against a step."""
        return self._launch_stack

    def _template(self, blueprint):
        """Generate a template based on whether or not an S3 bucket is set.

        If an S3 bucket is set, then the template will be uploaded to S3 first,
        and CreateStack/UpdateStack operations will use the uploaded template.
        If not bucket is set, then the template will be inlined.

        """
        if self.bucket_name:
            return Template(url=self.s3_stack_push(blueprint))
        return Template(body=blueprint.rendered)

    @staticmethod
    def _stack_policy(stack):
        """Return a Template object for the stacks stack policy.

        Returns:
            Template: If stack has a template policy
            None: If the stack doesn't have a stack policy.

        """
        if stack.stack_policy:
            return Template(body=stack.stack_policy)
        return None

    def __generate_plan(self, tail=False):
        """Plan creation that is specific to the build action.

        If a persistent graph is used, stacks that exist in the persistent
        graph but are no longer in the "local" graph will be deleted.
        If not using a persistent graph. the default method for creating
        a plan is used.

        Args:
            tail (Union[bool, Callable]): An optional function to call
                to tail the stack progress.

        Returns:
            :class:`runway.cfngin.plan.Plan`: The resulting plan object.

        """
        if not self.context.persistent_graph:
            return self._generate_plan(tail)

        graph = Graph()
        config_stack_names = [stack.name for stack in self.context.get_stacks()]
        inverse_steps = []
        persist_graph = self.context.persistent_graph.transposed()

        def target_fn(*_args, **_kwargs):
            """Target function."""
            return COMPLETE

        for ind_node, dep_nodes in persist_graph.dag.graph.items():
            if ind_node not in config_stack_names:
                inverse_steps.append(
                    Step.from_stack_name(
                        ind_node,
                        self.context,
                        requires=list(dep_nodes),
                        fn=self._destroy_stack,
                        watch_func=(self._tail_stack if tail else None),
                    )
                )

        graph.add_steps(inverse_steps)

        # invert what is going to be destroyed to retain dependencies
        graph = graph.transposed()

        steps = [
            Step(
                stack,
                fn=self._launch_stack,
                watch_func=(self._tail_stack if tail else None),
            )
            for stack in self.context.get_stacks()
        ]

        steps += [Step(target, fn=target_fn) for target in self.context.get_targets()]

        graph.add_steps(steps)

        return Plan(context=self.context, description=self.DESCRIPTION, graph=graph)

    def pre_run(self, **kwargs):
        """Any steps that need to be taken prior to running the action."""
        dump = kwargs.get("dump", False)
        outline = kwargs.get("outline", False)
        if should_ensure_cfn_bucket(outline, dump):
            self.ensure_cfn_bucket()
        hooks = self.context.config.pre_build
        handle_hooks("pre_build", hooks, self.provider, self.context, dump, outline)

    def run(self, **kwargs):
        """Kicks off the build/update of the stacks in the stack_definitions.

        This is the main entry point for the Builder.

        """
        dump = kwargs.get("dump", False)
        outline = kwargs.get("outline", False)
        plan = self.__generate_plan(tail=kwargs.get("tail"))
        if not plan.keys():
            LOGGER.warning("no stacks detected (error in config?)")
        if not outline and not dump:
            plan.outline(logging.DEBUG)
            self.context.lock_persistent_graph(plan.lock_code)
            LOGGER.debug("launching stacks: %s", ", ".join(plan.keys()))
            walker = build_walker(kwargs.get("concurrency", 0))
            try:
                plan.execute(walker)
            finally:
                # always unlock the graph at the end
                self.context.unlock_persistent_graph(plan.lock_code)
        else:
            if outline:
                plan.outline()
            if dump:
                plan.dump(directory=dump, context=self.context, provider=self.provider)

    def post_run(self, **kwargs):
        """Any steps that need to be taken after running the action."""
        dump = kwargs.get("dump", False)
        outline = kwargs.get("outline", False)
        hooks = self.context.config.post_build
        handle_hooks("post_build", hooks, self.provider, self.context, dump, outline)
