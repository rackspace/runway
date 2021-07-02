"""Default AWS Provider."""
# pylint: disable=too-many-lines,too-many-public-methods
from __future__ import annotations

import json
import logging
import sys
import threading
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)
from urllib.parse import urlparse, urlunparse

import botocore.exceptions
import yaml
from botocore.config import Config

from ....utils import DOC_SITE, JsonEncoder
from ... import exceptions
from ...actions.diff import DictValue, diff_parameters
from ...actions.diff import format_params_diff as format_diff
from ...session_cache import get_session
from ...ui import ui
from ...utils import parse_cloudformation_template
from ..base import BaseProvider

if TYPE_CHECKING:
    import boto3
    from mypy_boto3_cloudformation.client import CloudFormationClient
    from mypy_boto3_cloudformation.type_defs import (
        ChangeTypeDef,
        DescribeChangeSetOutputTypeDef,
        ParameterTypeDef,
        StackEventTypeDef,
        StackTypeDef,
    )

    from ...._logging import RunwayLogger
    from ....core.providers.aws.type_defs import TagTypeDef
    from ...stack import Stack
    from ..base import Template

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))

# This value controls the maximum number of times a CloudFormation API call
# will be attempted, after being throttled. This value is used in an
# exponential backoff algorithm to determine how long the client should wait
# until attempting a retry:
#
#   base * growth_factor ^ (attempts - 1)
#
# A value of 10 here would cause the worst case wait time for the last retry to
# be ~8 mins:
#
#   1 * 2 ^ (10 - 1) = 512 seconds
#
# References:
# https://github.com/boto/botocore/blob/1.6.1/botocore/retryhandler.py#L39-L58
# https://github.com/boto/botocore/blob/1.6.1/botocore/data/_retry.json#L97-L121
MAX_ATTEMPTS = 10

# Updated this to 15 retries with a 1 second sleep between retries. This is
# only used when a call to `get_events` fails due to the stack not being
# found. This is often the case because Cloudformation is taking too long
# to create the stack. 15 seconds should, hopefully, be plenty of time for
# the stack to start showing up in the API.
MAX_TAIL_RETRIES = 15
TAIL_RETRY_SLEEP = 1
GET_EVENTS_SLEEP = 1
DEFAULT_CAPABILITIES = ["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]


def get_cloudformation_client(session: boto3.Session) -> CloudFormationClient:
    """Get CloudFormaiton boto3 client."""
    config = Config(retries={"max_attempts": MAX_ATTEMPTS})
    return session.client("cloudformation", config=config)


def get_output_dict(stack: StackTypeDef) -> Dict[str, str]:
    """Return a dict of key/values for the outputs for a given CF stack.

    Args:
        stack: The stack object to get outputs from.

    Returns:
        A dictionary with key/values for each output on the stack.

    """
    if not stack.get("Outputs"):
        return {}
    outputs = {
        # both of these should exist even if the schema says they may not
        output["OutputKey"]: output["OutputValue"]  # type: ignore
        for output in stack.get("Outputs", [])
    }
    LOGGER.debug("%s stack outputs: %s", stack["StackName"], json.dumps(outputs))
    return outputs


def s3_fallback(
    fqn: str,
    template: Template,
    parameters: List[ParameterTypeDef],
    tags: List[TagTypeDef],
    method: Callable[..., Any],
    change_set_name: Optional[str] = None,
    service_role: Optional[str] = None,
) -> Any:
    """Falling back to legacy CFNgin S3 bucket region for templates."""
    LOGGER.warning(
        "falling back to deprecated, legacy CFNgin S3 bucket "
        "region for templates; to learn how to correctly provide an "
        "s3 bucket, visit %s/page/cfngin/configuration.html",
        DOC_SITE,
    )
    # extra line break on purpose to avoid status updates removing URL
    # from view
    LOGGER.warning("\n")
    LOGGER.debug("modifying the S3 TemplateURL to point to us-east-1 endpoint")
    template_url = template.url
    if template_url:
        template_url_parsed = urlparse(template_url)
        template_url_parsed = template_url_parsed._replace(netloc="s3.amazonaws.com")
        template_url = urlunparse(template_url_parsed)
    LOGGER.debug("using template_url: %s", template_url)
    args = generate_cloudformation_args(
        fqn,
        parameters,
        tags,
        template,
        service_role=service_role,
        change_set_name=change_set_name,
    )

    return method(**args)


def get_change_set_name() -> str:
    """Return a valid Change Set Name.

    The name has to satisfy the following regex::

        [a-zA-Z][-a-zA-Z0-9]*

    And must be unique across all change sets.

    """
    return f"change-set-{int(time.time())}"


def requires_replacement(changeset: List[ChangeTypeDef]) -> List[ChangeTypeDef]:
    """Return the changes within the changeset that require replacement.

    Args:
        changeset: List of changes

    """
    return [
        r
        for r in changeset
        if r.get("ResourceChange", {}).get("Replacement", False) == "True"
    ]


def output_full_changeset(
    full_changeset: Optional[List[ChangeTypeDef]] = None,
    params_diff: Optional[List[DictValue[Any, Any]]] = None,
    answer: Optional[str] = None,
    fqn: Optional[str] = None,
) -> None:
    """Optionally output full changeset.

    Args:
        full_changeset: A list of the full changeset that will be output if the
            user specifies verbose.
        params_diff: A list of DictValue detailing the differences between two
            parameters returned by :func:`runway.cfngin.actions.diff.diff_dictionaries`.
        answer: Predetermined answer to the prompt if it has already been answered or inferred.
        fqn: Fully qualified name of the stack.

    """
    if not answer:
        answer = ui.ask("Show full change set? [y/n] ").lower()
    if answer == "n":
        return
    if answer in ["y", "v"]:
        msg = f"{fqn if fqn else 'Full changeset'} full changeset"
        if params_diff:
            LOGGER.info(
                "%s:\n\n%s\n%s",
                msg,
                format_params_diff(params_diff),
                yaml.safe_dump(full_changeset),
            )
        else:
            LOGGER.info("%s:\n%s", msg, yaml.safe_dump(full_changeset))
        return
    raise exceptions.CancelExecution


def ask_for_approval(
    full_changeset: Optional[List[ChangeTypeDef]] = None,
    params_diff: Optional[List[DictValue[Any, Any]]] = None,
    include_verbose: bool = False,
    fqn: Optional[str] = None,
) -> None:
    """Prompt the user for approval to execute a change set.

    Args:
        full_changeset: A list of the full changeset that will be output if the
            user specifies verbose.
        params_diff: A list of DictValue detailing the differences between two
            parameters returned by :func:`runway.cfngin.actions.diff.diff_dictionaries`
        include_verbose: Boolean for whether or not to include the verbose option.
        fqn: fully qualified name of the stack.

    Raises:
        CancelExecution: If approval no given.

    """
    approval_options = ["y", "n"]
    if include_verbose:
        approval_options.append("v")

    approve = ui.ask(
        f"Execute the above changes? [{'/'.join(approval_options)}] "
    ).lower()

    if include_verbose and approve == "v":
        output_full_changeset(
            full_changeset=full_changeset,
            params_diff=params_diff,
            answer=approve,
            fqn=fqn,
        )
        return ask_for_approval(fqn=fqn)
    if approve == "y":
        return None
    raise exceptions.CancelExecution


def output_summary(
    fqn: str,
    action: str,
    changeset: List[ChangeTypeDef],
    params_diff: List[DictValue[Any, Any]],
    replacements_only: bool = False,
) -> None:
    """Log a summary of the changeset.

    Args:
        fqn: Fully qualified name of the stack.
        action: Action to include in the log message.
        changeset: AWS changeset.
        params_diff: A list of dictionaries detailing the differences
            between two parameters returned by
            :func:`runway.cfngin.actions.diff.diff_dictionaries`
        replacements_only: Boolean for whether or not we only want to list
            replacements.

    """
    replacements: List[Any] = []
    changes: List[Any] = []
    for change in changeset:
        resource = change.get("ResourceChange", {})
        replacement = resource.get("Replacement", "") == "True"
        summary = (
            f"- {resource.get('Action')} {resource.get('LogicalResourceId')} "
            f"({resource.get('ResourceType')})"
        )
        if replacement:
            replacements.append(summary)
        else:
            changes.append(summary)

    summary = ""
    if params_diff:
        summary += summarize_params_diff(params_diff)
    if replacements:
        if not replacements_only:
            summary += "Replacements:\n"
        summary += "\n".join(replacements)
    if changes:
        if summary:
            summary += "\n"
        summary += "Changes:\n" + "\n".join(changes)
    LOGGER.info("%s %s:\n%s", fqn, action, summary)


def format_params_diff(params_diff: List[DictValue[Any, Any]]) -> str:
    """Wrap :func:`runway.cfngin.actions.diff.format_params_diff` for testing."""
    return format_diff(params_diff)


def summarize_params_diff(params_diff: List[DictValue[Any, Any]]) -> str:
    """Summarize parameter diff."""
    summary = ""

    added_summary = [v.key for v in params_diff if v.status() is DictValue.ADDED]
    if added_summary:
        summary += f"Parameters Added: {', '.join(added_summary)}\n"

    removed_summary = [v.key for v in params_diff if v.status() is DictValue.REMOVED]
    if removed_summary:
        summary += f"Parameters Removed: {', '.join(removed_summary)}\n"

    modified_summary = [v.key for v in params_diff if v.status() is DictValue.MODIFIED]
    if modified_summary:
        summary += f"Parameters Modified: {', '.join(modified_summary)}\n"

    return summary


def wait_till_change_set_complete(
    cfn_client: CloudFormationClient,
    change_set_id: str,
    try_count: int = 25,
    sleep_time: float = 0.5,
    max_sleep: float = 3,
) -> DescribeChangeSetOutputTypeDef:
    """Check state of a changeset, returning when it is in a complete state.

    Since changesets can take a little bit of time to get into a complete
    state, we need to poll it until it does so. This will try to get the
    state ``try_count`` times, waiting ``sleep_time`` * 2 seconds between each
    try up to the ``max_sleep`` number of seconds. If, after that time, the
    changeset is not in a complete state it fails. These default settings will
    wait a little over one minute.

    Args:
        cfn_client: Used to query CloudFormation.
        change_set_id: The unique changeset id to wait for.
        try_count: Number of times to try the call.
        sleep_time: Time to sleep between attempts.
        max_sleep: Max time to sleep during backoff

    """
    complete = False
    for _ in range(try_count):
        response = cfn_client.describe_change_set(ChangeSetName=change_set_id)
        complete = response["Status"] in ("FAILED", "CREATE_COMPLETE")
        if complete:
            return response
        if sleep_time == max_sleep:
            LOGGER.debug("waiting on changeset for another %s seconds", sleep_time)
        time.sleep(sleep_time)

        # exponential backoff with max
        sleep_time = min(sleep_time * 2, max_sleep)
    raise exceptions.ChangesetDidNotStabilize(change_set_id)


def create_change_set(
    cfn_client: CloudFormationClient,
    fqn: str,
    template: Template,
    parameters: List[ParameterTypeDef],
    tags: List[TagTypeDef],
    change_set_type: str = "UPDATE",
    service_role: Optional[str] = None,
) -> Tuple[List[ChangeTypeDef], str]:
    """Create CloudFormation change set."""
    LOGGER.debug(
        "attempting to create change set of type %s for stack: %s", change_set_type, fqn
    )
    args = generate_cloudformation_args(
        fqn,
        parameters,
        tags,
        template,
        change_set_type=change_set_type,
        service_role=service_role,
        change_set_name=get_change_set_name(),
    )
    try:
        response = cfn_client.create_change_set(**args)
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Message"] == (
            "TemplateURL must reference a valid S3 object to which you have access."
        ):
            response = s3_fallback(
                fqn,
                template,
                parameters,
                tags,
                cfn_client.create_change_set,
                get_change_set_name(),
                service_role,
            )
        else:
            raise
    change_set_id = response["Id"]
    response = wait_till_change_set_complete(cfn_client, change_set_id)
    status = response["Status"]
    if status == "FAILED":
        status_reason = response["StatusReason"]
        if (
            "didn't contain changes" in status_reason
            or "No updates are to be performed" in status_reason
        ):
            LOGGER.debug(
                "%s:stack did not change; not updating and removing changeset", fqn
            )
            cfn_client.delete_change_set(ChangeSetName=change_set_id)
            raise exceptions.StackDidNotChange()
        LOGGER.warning(
            "got strange status, '%s' for changeset '%s'; not deleting for "
            "further investigation - you will need to delete the changeset manually",
            status,
            change_set_id,
        )
        raise exceptions.UnhandledChangeSetStatus(
            fqn, change_set_id, status, status_reason
        )

    execution_status = response["ExecutionStatus"]
    if execution_status != "AVAILABLE":
        raise exceptions.UnableToExecuteChangeSet(fqn, change_set_id, execution_status)

    changes = response["Changes"]
    return changes, change_set_id


def check_tags_contain(actual: List[TagTypeDef], expected: List[TagTypeDef]) -> bool:
    """Check if a set of AWS resource tags is contained in another.

    Every tag key in ``expected`` must be present in ``actual``, and have the
    same value. Extra keys in `actual` but not in ``expected`` are ignored.

    Args:
        actual: Set of tags to be verified, usually
            from the description of a resource. Each item must be a
            ``dict`` containing ``Key`` and ``Value`` items.
        expected: Set of tags that must be present in
            ``actual`` (in the same format).

    """
    actual_set = {(item["Key"], item["Value"]) for item in actual}
    expected_set = {(item["Key"], item["Value"]) for item in expected}

    return actual_set >= expected_set


def generate_cloudformation_args(
    stack_name: str,
    parameters: List[ParameterTypeDef],
    tags: List[TagTypeDef],
    template: Template,
    capabilities: Optional[List[str]] = None,
    change_set_type: Optional[str] = None,
    service_role: Optional[str] = None,
    stack_policy: Optional[Template] = None,
    change_set_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate the args for common CloudFormation API interactions.

    This is used for ``create_stack``/``update_stack``/``create_change_set``
    calls in CloudFormation.

    Args:
        stack_name: The fully qualified stack name in Cloudformation.
        parameters: A list of dictionaries that defines the parameter list to be
            applied to the Cloudformation stack.
        tags: A list of dictionaries that defines the tags that should be applied
            to the Cloudformation stack.
        template: The template object.
        capabilities: A list of capabilities to use when updating Cloudformation.
        change_set_type: An optional change set type to use with create_change_set.
        service_role: An optional service role to use when interacting with
            Cloudformation.
        stack_policy: A template object representing a stack policy.
        change_set_name: An optional change set name to use with create_change_set.

    """
    args = {
        "StackName": stack_name,
        "Parameters": parameters,
        "Tags": tags,
        "Capabilities": capabilities or DEFAULT_CAPABILITIES,
    }

    if service_role:
        args["RoleARN"] = service_role

    if change_set_name:
        args["ChangeSetName"] = change_set_name

    if change_set_type:
        args["ChangeSetType"] = change_set_type

    if template.url:
        args["TemplateURL"] = template.url
    elif template.body:
        args["TemplateBody"] = template.body
    else:
        raise ValueError(
            "either template.body or template.url is required; neither were provided"
        )

    # When creating args for CreateChangeSet, don't include the stack policy,
    # since ChangeSets don't support it.
    if not change_set_name:
        args.update(generate_stack_policy_args(stack_policy))

    return args


def generate_stack_policy_args(
    stack_policy: Optional[Template] = None,
) -> Dict[str, str]:
    """Convert a stack policy object into keyword args.

    Args:
        stack_policy: A template object representing a stack policy.

    """
    args: Dict[str, str] = {}
    if stack_policy:
        LOGGER.debug("stack has a stack policy")
        if stack_policy.url:
            # CFNgin currently does not support uploading stack policies to
            # S3, so this will never get hit (unless your implementing S3
            # uploads, and then you're probably reading this comment about why
            # the exception below was raised :))
            #
            # args["StackPolicyURL"] = stack_policy.url
            raise NotImplementedError
        args["StackPolicyBody"] = cast(str, stack_policy.body)
    return args


class ProviderBuilder:
    """Implements a Memorized ProviderBuilder for the AWS provider."""

    kwargs: Dict[str, Any]
    lock: threading.Lock
    providers: Dict[str, Provider]
    region: Optional[str]

    def __init__(self, *, region: Optional[str] = None, **kwargs: Any) -> None:
        """Instantiate class."""
        self.region = region
        self.kwargs = kwargs
        self.providers = {}
        self.lock = threading.Lock()

    def build(
        self, *, profile: Optional[str] = None, region: Optional[str] = None
    ) -> Provider:
        """Get or create the provider for the given region and profile."""
        with self.lock:
            # memorization lookup key derived from region + profile.
            key = f"{profile}-{region}"
            try:
                # assume provider is in provider dictionary.
                provider = self.providers[key]
            except KeyError:
                LOGGER.debug(
                    "missed memorized lookup (%s); creating new AWS provider", key
                )
                if not region:
                    region = self.region
                # memoize the result for later.
                self.providers[key] = Provider(
                    get_session(region=region, profile=profile),
                    region=region,
                    **self.kwargs,
                )
                provider = self.providers[key]

        return provider


class Provider(BaseProvider):
    """AWS CloudFormation Provider."""

    COMPLETE_STATUSES = (
        "CREATE_COMPLETE",
        "DELETE_COMPLETE",
        "IMPORT_COMPLETE",
        "IMPORT_ROLLBACK_COMPLETE",
        "UPDATE_COMPLETE",
        "UPDATE_ROLLBACK_COMPLETE",
    )
    DELETE_IMPOSSIBLE_STATUS = "DELETE_FAILED"
    DELETED_STATUS = "DELETE_COMPLETE"
    DELETING_STATUS = "DELETE_IN_PROGRESS"
    FAILED_STATUSES = (
        "CREATE_FAILED",
        "DELETE_FAILED",
        "IMPORT_ROLLBACK_FAILED",
        "ROLLBACK_COMPLETE",
        "ROLLBACK_FAILED",
        # Note: UPDATE_ROLLBACK_COMPLETE is in both the FAILED and COMPLETE
        # sets, because we need to wait for it when a rollback is triggered,
        # but still mark the stack as failed.
        "UPDATE_ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_FAILED",
    )
    IN_PROGRESS_STATUSES = (
        "CREATE_IN_PROGRESS",
        "DELETE_IN_PROGRESS",
        "IMPORT_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
    )
    RECREATION_STATUSES = ("CREATE_FAILED", "ROLLBACK_COMPLETE", "ROLLBACK_FAILED")
    REVIEW_STATUS = "REVIEW_IN_PROGRESS"
    ROLLING_BACK_STATUSES = (
        "IMPORT_ROLLBACK_IN_PROGRESS",
        "ROLLBACK_IN_PROGRESS",
        "UPDATE_ROLLBACK_IN_PROGRESS",
    )

    cloudformation: CloudFormationClient
    interactive: bool
    recreate_failed: bool
    region: Optional[str]
    replacements_only: bool
    service_role: Optional[str]

    def __init__(
        self,
        session: boto3.Session,
        *,
        interactive: bool = False,
        recreate_failed: bool = False,
        region: Optional[str] = None,
        replacements_only: bool = False,
        service_role: Optional[str] = None,
    ):
        """Instantiate class."""
        self._outputs: Dict[str, Dict[str, str]] = {}
        self.cloudformation = get_cloudformation_client(session)
        self.interactive = interactive
        self.recreate_failed = interactive or recreate_failed
        self.region = region
        # replacements only is only used in interactive mode
        self.replacements_only = interactive and replacements_only
        self.service_role = service_role

    def get_stack(self, stack_name: str, *_args: Any, **_kwargs: Any) -> StackTypeDef:
        """Get stack."""
        try:
            return self.cloudformation.describe_stacks(StackName=stack_name)["Stacks"][
                0
            ]
        except botocore.exceptions.ClientError as err:
            if "does not exist" not in str(err):
                raise
            raise exceptions.StackDoesNotExist(stack_name)

    @staticmethod
    def get_stack_status(stack: StackTypeDef, *_args: Any, **_kwargs: Any) -> str:
        """Get stack status."""
        return stack["StackStatus"]

    @staticmethod
    def get_stack_status_reason(stack: StackTypeDef) -> Optional[str]:
        """Get stack status reason."""
        return stack.get("StackStatusReason")

    def is_stack_being_destroyed(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'being destroyed'."""
        return self.get_stack_status(stack) == self.DELETING_STATUS

    def is_stack_completed(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'complete'."""
        return self.get_stack_status(stack) in self.COMPLETE_STATUSES

    def is_stack_destroy_possible(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack is able to be cleanly deleted."""
        return self.get_stack_status(stack) != self.DELETE_IMPOSSIBLE_STATUS

    def is_stack_in_progress(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'in progress'."""
        return self.get_stack_status(stack) in self.IN_PROGRESS_STATUSES

    def is_stack_destroyed(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'deleted'."""
        return self.get_stack_status(stack) == self.DELETED_STATUS

    def is_stack_recreatable(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'recreating'."""
        return self.get_stack_status(stack) in self.RECREATION_STATUSES

    def is_stack_rolling_back(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'rolling back'."""
        return self.get_stack_status(stack) in self.ROLLING_BACK_STATUSES

    def is_stack_failed(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates it is 'failed'."""
        return self.get_stack_status(stack) in self.FAILED_STATUSES

    def is_stack_in_review(self, stack: StackTypeDef) -> bool:
        """Whether the status of the stack indicates if 'review in progress'."""
        return self.get_stack_status(stack) == self.REVIEW_STATUS

    def tail_stack(
        self,
        stack: Stack,
        cancel: threading.Event,
        action: Optional[str] = None,
        log_func: Optional[Callable[[StackEventTypeDef], None]] = None,
        retries: Optional[int] = None,
    ) -> None:
        """Tail the events of a stack."""

        def _log_func(event: StackEventTypeDef) -> None:
            template = "[%s] %s %s %s"
            event_args = [
                event.get("LogicalResourceId"),
                event.get("ResourceType"),
                event.get("ResourceStatus"),
            ]
            if event.get("ResourceStatusReason"):
                template += " (%s)"
                event_args.append(event.get("ResourceStatusReason"))
            event_args.insert(0, stack.fqn)
            LOGGER.verbose(template, *event_args)

        log_func = log_func or _log_func
        retries = retries or MAX_TAIL_RETRIES

        LOGGER.debug("%s:tailing stack...", stack.fqn)

        attempts = 0
        while True:
            attempts += 1
            try:
                self.tail(
                    stack.fqn, cancel=cancel, log_func=log_func, include_initial=False
                )
                break
            except botocore.exceptions.ClientError as err:
                if "does not exist" in str(err):
                    LOGGER.debug(
                        "%s:unable to tail stack; it does not exist", stack.fqn
                    )
                    if action == "destroy":
                        LOGGER.debug(
                            "%s:stack was deleted before it could be tailed", stack.fqn
                        )
                        return
                    if attempts < retries:
                        # stack might be in the process of launching, wait for a
                        # second and try again
                        if cancel.wait(TAIL_RETRY_SLEEP):
                            return
                        continue
                raise

    @staticmethod
    def _tail_print(event: StackEventTypeDef) -> None:
        print(  # noqa: T001
            "%s %s %s"
            % (
                event.get("ResourceStatus"),
                event.get("ResourceType"),
                event.get("EventId"),
            )
        )

    def get_delete_failed_status_reason(self, stack_name: str) -> Optional[str]:
        """Process events and return latest delete failed reason.

        Args:
            stack_name: Name of a CloudFormation Stack.

        Returns:
            Reason for the Stack's DELETE_FAILED status if one can be found.

        """
        event: Union[Dict[str, str], StackEventTypeDef] = (
            self.get_event_by_resource_status(
                stack_name, "DELETE_FAILED", chronological=True
            )
            or {}
        )
        return event.get("ResourceStatusReason")

    def get_event_by_resource_status(
        self, stack_name: str, status: str, *, chronological: bool = True
    ) -> Optional[StackEventTypeDef]:
        """Get Stack Event of a given set of resource status.

        Args:
            stack_name: Name of a CloudFormation Stack.
            status: Resource status to look for.
            chronological: Whether to sort events in chronological order before
                looking for the desired status.

        Returns:
            The first Stack Event matching the given status.

        """
        return next(
            (
                event
                for event in self.get_events(stack_name, chronological=chronological)
                if event.get("ResourceStatus") == status
            ),
            None,
        )

    def get_events(
        self, stack_name: str, chronological: bool = True
    ) -> Iterable[StackEventTypeDef]:
        """Get the events in batches and return in chronological order."""
        next_token = None
        event_list: List[List[StackEventTypeDef]] = []
        while True:
            if next_token is not None:
                events = self.cloudformation.describe_stack_events(
                    StackName=stack_name, NextToken=next_token
                )
            else:
                events = self.cloudformation.describe_stack_events(StackName=stack_name)
            event_list.append(events["StackEvents"])
            next_token = events.get("NextToken", None)
            if next_token is None:
                break
            time.sleep(GET_EVENTS_SLEEP)
        if chronological:
            return cast(
                Iterable["StackEventTypeDef"],
                reversed(
                    cast(List["StackEventTypeDef"], sum(event_list, []))  # type: ignore
                ),
            )
        return cast(Iterable["StackEventTypeDef"], sum(event_list, []))  # type: ignore

    def get_rollback_status_reason(self, stack_name: str) -> Optional[str]:
        """Process events and returns latest roll back reason.

        Args:
            stack_name: Name of a CloudFormation Stack.

        Returns:
            Reason for the Stack's rollback status if one can be found.

        """
        event: Union[Dict[str, str], StackEventTypeDef] = (
            self.get_event_by_resource_status(
                stack_name, "UPDATE_ROLLBACK_IN_PROGRESS", chronological=False
            )
            or self.get_event_by_resource_status(
                stack_name, "ROLLBACK_IN_PROGRESS", chronological=True
            )
            or {}
        )
        return event.get("ResourceStatusReason")

    def tail(
        self,
        stack_name: str,
        cancel: threading.Event,
        log_func: Callable[[StackEventTypeDef], None] = _tail_print,
        sleep_time: int = 5,
        include_initial: bool = True,
    ) -> None:
        """Show and then tail the event log."""
        # First dump the full list of events in chronological order and keep
        # track of the events we've seen already
        seen: Set[str] = set()
        initial_events = self.get_events(stack_name)
        for event in initial_events:
            if include_initial:
                log_func(event)
            seen.add(event["EventId"])

        # Now keep looping through and dump the new events
        while True:
            events = self.get_events(stack_name)
            for event in events:
                if event["EventId"] not in seen:
                    log_func(event)
                    seen.add(event["EventId"])
            if cancel.wait(sleep_time):
                return

    def destroy_stack(
        self,
        stack: StackTypeDef,
        *,
        action: str = "destroy",
        approval: Optional[str] = None,
        force_interactive: bool = False,
        **kwargs: Any,
    ) -> None:
        """Destroy a CloudFormation Stack.

        Args:
            stack: Stack to be destroyed.
            action: Name of the action being executed. This impacts the log message used.
            approval: Response to approval prompt.
            force_interactive: Always ask for approval.

        """
        fqn = self.get_stack_name(stack)
        LOGGER.debug("%s:attempting to delete stack", fqn)

        if action == "deploy":
            LOGGER.info(
                "%s:removed from the CFNgin config file; it is being destroyed", fqn
            )

        destroy_method = self.select_destroy_method(force_interactive)
        return destroy_method(fqn=fqn, action=action, approval=approval, **kwargs)

    def create_stack(
        self,
        fqn: str,
        template: Template,
        parameters: List[ParameterTypeDef],
        tags: List[TagTypeDef],
        *,
        force_change_set: bool = False,
        stack_policy: Optional[Template] = None,
        termination_protection: bool = False,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Create a new Cloudformation stack.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            template: A Template object to use when creating the stack.
            parameters: A list of dictionaries that defines the parameter list
                to be applied to the Cloudformation stack.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.
            force_change_set: Whether or not to force change set use.
            stack_policy: A template object representing a stack policy.
            termination_protection: End state of the stack's termination
                protection.
            timeout: The amount of time that can pass before the stack status becomes
                ``CREATE_FAILED``.

        """
        LOGGER.debug(
            "attempting to create stack %s: %s",
            fqn,
            json.dumps(
                {"parameters": parameters, "tags": tags, "template_url": template.url}
            ),
        )
        if not template.url:
            LOGGER.debug("no template url; uploading template directly")
        if force_change_set:
            LOGGER.debug("force_change_set set to True; creating stack with changeset")
            _changes, change_set_id = create_change_set(
                self.cloudformation,
                fqn,
                template,
                parameters,
                tags,
                "CREATE",
                service_role=self.service_role,
                **kwargs,
            )

            self.cloudformation.execute_change_set(ChangeSetName=change_set_id)
            self.update_termination_protection(fqn, termination_protection)
        else:
            args = generate_cloudformation_args(
                fqn,
                parameters,
                tags,
                template,
                service_role=self.service_role,
                stack_policy=stack_policy,
            )
            # these args are only valid for stack creation so they are not part of
            # generate_cloudformation_args.
            args["EnableTerminationProtection"] = termination_protection
            if timeout:
                args["TimeoutInMinutes"] = timeout

            try:
                self.cloudformation.create_stack(**args)
            except botocore.exceptions.ClientError as err:
                if err.response["Error"]["Message"] == (
                    "TemplateURL must reference a valid S3 object to which you "
                    "have access."
                ):
                    s3_fallback(
                        fqn,
                        template,
                        parameters,
                        tags,
                        self.cloudformation.create_stack,
                        self.service_role,
                    )
                else:
                    raise

    def select_update_method(
        self, force_interactive: bool, force_change_set: bool
    ) -> Callable[..., None]:
        """Select the correct update method when updating a stack.

        Args:
            force_interactive: Whether or not to force interactive mode
                no matter what mode the provider is in.
            force_change_set: Whether or not to force change set use.

        Returns:
            function: The correct object method to use when updating.

        """
        if self.interactive or force_interactive:
            return self.interactive_update_stack
        if force_change_set:
            return self.noninteractive_changeset_update
        return self.default_update_stack

    def prepare_stack_for_update(
        self, stack: StackTypeDef, tags: List[TagTypeDef]
    ) -> bool:
        """Prepare a stack for updating.

        It may involve deleting the stack if is has failed it's initial
        creation. The deletion is only allowed if:

        - The stack contains all the tags configured in the current context;
        - The stack is in one of the statuses considered safe to re-create
        - ``recreate_failed`` is enabled, due to either being explicitly
          enabled by the user, or because interactive mode is on.

        Args:
            stack: A stack object returned from get_stack
            tags: List of expected tags that must be present in the stack if it
                must be re-created

        Returns:
            True if the stack can be updated, False if it must be re-created

        """
        if self.is_stack_destroyed(stack):
            return False
        if self.is_stack_completed(stack):
            return True

        stack_name = self.get_stack_name(stack)
        stack_status = self.get_stack_status(stack)

        if self.is_stack_in_progress(stack):
            raise exceptions.StackUpdateBadStatus(
                stack_name, stack_status, "Update already in-progress"
            )

        if not self.is_stack_recreatable(stack):
            raise exceptions.StackUpdateBadStatus(
                stack_name, stack_status, "Unsupported state for re-creation"
            )

        if not self.recreate_failed:
            raise exceptions.StackUpdateBadStatus(
                stack_name,
                stack_status,
                "Stack re-creation is disabled. Run CFNgin again with the "
                "--recreate-failed option to force it to be deleted and "
                "created from scratch.",
            )

        stack_tags = self.get_stack_tags(stack)
        if not check_tags_contain(stack_tags, tags):
            raise exceptions.StackUpdateBadStatus(
                stack_name,
                stack_status,
                "Tags differ from current configuration, possibly not created "
                "with CFNgin",
            )

        if self.interactive:
            sys.stdout.write(
                f'The "{stack_name}" stack is in a failed state ({stack_status}).\n'
                "It cannot be updated, but it can be deleted and re-created.\n"
                "All its current resources will IRREVERSIBLY DESTROYED.\n"
                "Proceed carefully!\n\n"
            )
            sys.stdout.flush()

            ask_for_approval(include_verbose=False, fqn=stack_name)

        LOGGER.warning("%s:destroying stack for re-creation", stack_name)
        self.destroy_stack(stack, approval="y")

        return False

    def update_stack(
        self,
        fqn: str,
        template: Template,
        old_parameters: List[ParameterTypeDef],
        parameters: List[ParameterTypeDef],
        tags: List[TagTypeDef],
        force_interactive: bool = False,
        force_change_set: bool = False,
        stack_policy: Optional[Template] = None,
        termination_protection: bool = False,
        **kwargs: Any,
    ) -> None:
        """Update a Cloudformation stack.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            template: A Template object to use when updating the stack.
            old_parameters: A list of dictionaries that defines the parameter
                list on the existing Cloudformation stack.
            parameters: A list of dictionaries that defines the parameter list to
                be applied to the Cloudformation stack.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.
            force_interactive : A flag that indicates whether the update
                should be interactive. If set to True, interactive mode will
                be used no matter if the provider is in interactive mode or
                not. False will follow the behavior of the provider.
            force_change_set: A flag that indicates whether the update must be
                executed with a change set.
            stack_policy: A template object representing a stack policy.
            termination_protection: End state of the stack's termination protection.

        """
        LOGGER.debug(
            "attempting to update stack %s: %s",
            fqn,
            json.dumps(
                {"parameters": parameters, "tags": tags, "template_url": template.url}
            ),
        )
        if not template.url:
            LOGGER.debug("no template url; uploading template directly")
        update_method = self.select_update_method(force_interactive, force_change_set)

        self.update_termination_protection(fqn, termination_protection)
        return update_method(
            fqn,
            template,
            old_parameters,
            parameters,
            stack_policy=stack_policy,
            tags=tags,
            **kwargs,
        )

    def update_termination_protection(
        self, fqn: str, termination_protection: bool
    ) -> None:
        """Update a Stack's termination protection if needed.

        Runs before the normal stack update process.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            termination_protection: End state of the stack's termination protection.

        """
        stack = self.get_stack(fqn)

        if stack.get("EnableTerminationProtection", False) != termination_protection:
            LOGGER.debug(
                '%s:updating termination protection of stack to "%s"',
                fqn,
                termination_protection,
            )
            self.cloudformation.update_termination_protection(
                EnableTerminationProtection=termination_protection, StackName=fqn
            )

    def deal_with_changeset_stack_policy(
        self, fqn: str, stack_policy: Optional[Template] = None
    ) -> None:
        """Set a stack policy when using changesets.

        ChangeSets don't allow you to set stack policies in the same call to
        update them. This sets it before executing the changeset if the
        stack policy is passed in.

        Args:
            fqn: Fully qualified name of the stack.
            stack_policy: A template object representing a stack policy.

        """
        if stack_policy:
            kwargs = generate_stack_policy_args(stack_policy)
            kwargs["StackName"] = fqn
            LOGGER.debug("%s:adding stack policy", fqn)
            self.cloudformation.set_stack_policy(**kwargs)

    def interactive_destroy_stack(
        self, fqn: str, approval: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Delete a CloudFormation stack in interactive mode.

        Args:
            fqn: A fully qualified stack name.
            approval: Response to approval prompt.

        """
        LOGGER.debug("%s:using interactive provider mode", fqn)
        action = kwargs.get("action", "destroy")

        approval_options = ["y", "n"]
        with ui:
            description = "temporary " if action == "diff" else ""
            detail = " created to generate a change set" if action == "diff" else ""
            approval = (
                approval
                or ui.ask(
                    f"Destroy {description}stack '{fqn}'{detail}? [{'/'.join(approval_options)}] "
                ).lower()
            )

        if approval != "y":
            raise exceptions.CancelExecution

        try:
            return self.noninteractive_destroy_stack(fqn, **kwargs)
        except botocore.exceptions.ClientError as err:
            if "TerminationProtection" in err.response["Error"]["Message"]:
                approval = ui.ask(
                    "Termination protection is enabled for "
                    f"stack '{fqn}'.\nWould you like to disable it "
                    "and try destroying the stack again? "
                    f"[{'/'.join(approval_options)}] "
                ).lower()
                if approval == "y":
                    self.update_termination_protection(fqn, False)
                    return self.noninteractive_destroy_stack(fqn, **kwargs)
            raise

    def interactive_update_stack(
        self,
        fqn: str,
        template: Template,
        old_parameters: List[ParameterTypeDef],
        parameters: List[ParameterTypeDef],
        stack_policy: Template,
        tags: List[TagTypeDef],
    ) -> None:
        """Update a Cloudformation stack in interactive mode.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            template: A Template object to use when updating the stack.
            old_parameters: A list of dictionaries that defines the parameter
                list on the existing Cloudformation stack.
            parameters: A list of dictionaries that defines the parameter list
                to be applied to the Cloudformation stack.
            stack_policy: A template object representing a stack policy.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.

        """
        LOGGER.debug("%s:using interactive provider mode", fqn)
        changes, change_set_id = create_change_set(
            self.cloudformation,
            fqn,
            template,
            parameters,
            tags,
            "UPDATE",
            service_role=self.service_role,
        )
        old_parameters_as_dict = self.params_as_dict(old_parameters)
        new_parameters_as_dict = self.params_as_dict(
            [
                x
                if "ParameterValue" in x
                else {
                    "ParameterKey": x["ParameterKey"],  # type: ignore
                    "ParameterValue": old_parameters_as_dict[x["ParameterKey"]],  # type: ignore
                }
                for x in parameters
            ]
        )
        params_diff = diff_parameters(old_parameters_as_dict, new_parameters_as_dict)

        action = "replacements" if self.replacements_only else "changes"
        full_changeset = changes
        if self.replacements_only:
            changes = requires_replacement(changes)

        if changes or params_diff:
            with ui:
                output_summary(
                    fqn,
                    action,
                    changes,
                    params_diff,
                    replacements_only=self.replacements_only,
                )
                ask_for_approval(
                    full_changeset=full_changeset,
                    params_diff=params_diff,
                    include_verbose=True,
                    fqn=fqn,
                )

        self.deal_with_changeset_stack_policy(fqn, stack_policy)

        self.cloudformation.execute_change_set(ChangeSetName=change_set_id)

    def noninteractive_destroy_stack(self, fqn: str, **_kwargs: Any) -> None:
        """Delete a CloudFormation stack without interaction.

        Args:
            fqn: A fully qualified stack name.

        """
        LOGGER.debug("%s:destroying stack", fqn)
        args = {"StackName": fqn}
        if self.service_role:
            args["RoleARN"] = self.service_role

        self.cloudformation.delete_stack(**args)

    def noninteractive_changeset_update(  # pylint: disable=unused-argument
        self,
        fqn: str,
        template: Template,
        old_parameters: List[ParameterTypeDef],
        parameters: List[ParameterTypeDef],
        stack_policy: Optional[Template],
        tags: List[TagTypeDef],
    ) -> None:
        """Update a Cloudformation stack using a change set.

        This is required for stacks with a defined Transform (i.e. SAM), as the
        default ``update_stack`` API cannot be used with them.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            template: A Template object to use when updating the stack.
            old_parameters: A list of dictionaries that defines the parameter
                list on the existing Cloudformation stack.
            parameters: A list of dictionaries that defines the parameter list
                to be applied to the Cloudformation stack.
            stack_policy: A template object representing a stack policy.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.

        """
        LOGGER.debug("%s:using non-interactive changeset provider mode", fqn)
        _changes, change_set_id = create_change_set(
            self.cloudformation,
            fqn,
            template,
            parameters,
            tags,
            "UPDATE",
            service_role=self.service_role,
        )

        self.deal_with_changeset_stack_policy(fqn, stack_policy)

        self.cloudformation.execute_change_set(ChangeSetName=change_set_id)

    def select_destroy_method(self, force_interactive: bool) -> Callable[..., None]:
        """Select the correct destroy method for destroying a stack.

        Args:
            force_interactive: Always ask for approval.

        Returns:
            Interactive or non-interactive method to be invoked.

        """
        if self.interactive or force_interactive:
            return self.interactive_destroy_stack
        return self.noninteractive_destroy_stack

    def default_update_stack(  # pylint: disable=unused-argument
        self,
        fqn: str,
        template: Template,
        old_parameters: List[ParameterTypeDef],
        parameters: List[ParameterTypeDef],
        tags: List[TagTypeDef],
        stack_policy: Optional[Template] = None,
    ) -> None:
        """Update a Cloudformation stack in default mode.

        Args:
            fqn: The fully qualified name of the Cloudformation stack.
            template: A Template object to use when updating the stack.
            old_parameters: A list of dictionaries that defines the parameter
                list on the existing Cloudformation stack.
            parameters: A list of dictionaries that defines the parameter list
                to be applied to the Cloudformation stack.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.
            stack_policy: A template object representing a stack policy.

        """
        LOGGER.debug("%s:using default provider mode", fqn)
        args = generate_cloudformation_args(
            fqn,
            parameters,
            tags,
            template,
            service_role=self.service_role,
            stack_policy=stack_policy,
        )

        try:
            self.cloudformation.update_stack(**args)
        except botocore.exceptions.ClientError as err:
            if "No updates are to be performed." in str(err):
                LOGGER.debug("%s:stack did not change; not updating", fqn)
                raise exceptions.StackDidNotChange
            if err.response["Error"]["Message"] == (
                "TemplateURL must reference a valid S3 object to which you have access."
            ):
                s3_fallback(
                    fqn,
                    template,
                    parameters,
                    tags,
                    self.cloudformation.update_stack,
                    self.service_role,
                )
            raise

    @staticmethod
    def get_stack_name(stack: StackTypeDef) -> str:
        """Get stack name."""
        return stack["StackName"]

    @staticmethod
    def get_stack_tags(stack: StackTypeDef) -> List[TagTypeDef]:
        """Get stack tags."""
        return stack.get("Tags", [])

    def get_outputs(
        self, stack_name: str, *_args: Any, **_kwargs: Any
    ) -> Dict[str, str]:
        """Get stack outputs."""
        if not self._outputs.get(stack_name):
            stack = self.get_stack(stack_name)
            self._outputs[stack_name] = get_output_dict(stack)
        return self._outputs[stack_name]

    @staticmethod
    def get_output_dict(stack: StackTypeDef) -> Dict[str, str]:
        """Get stack outputs dict."""
        return get_output_dict(stack)

    def get_stack_info(
        self, stack: StackTypeDef
    ) -> Tuple[str, Dict[str, Union[List[str], str]]]:
        """Get the template and parameters of the stack currently in AWS."""
        stack_name = stack.get("StackId", "None")

        try:
            template = self.cloudformation.get_template(StackName=stack_name)[
                "TemplateBody"
            ]
        except botocore.exceptions.ClientError as err:
            if "does not exist" not in str(err):
                raise
            raise exceptions.StackDoesNotExist(stack_name)

        parameters = self.params_as_dict(stack.get("Parameters", []))

        # handle yaml templates
        if isinstance(template, str):  # type: ignore
            template = parse_cloudformation_template(template)

        return json.dumps(template, cls=JsonEncoder), parameters

    def get_stack_changes(
        self,
        stack: Stack,
        template: Template,
        parameters: List[ParameterTypeDef],
        tags: List[TagTypeDef],
    ) -> Dict[str, str]:
        """Get the changes from a ChangeSet.

        Args:
            stack: The stack to get changes.
            template: A Template object to compaired to.
            parameters: A list of dictionaries that defines the parameter list
                to be applied to the Cloudformation stack.
            tags: A list of dictionaries that defines the tags that should be
                applied to the Cloudformation stack.

        Returns:
            Stack outputs with inferred changes.

        """
        try:
            stack_details = self.get_stack(stack.fqn)
            # handling for orphaned changeset temp stacks
            if self.get_stack_status(stack_details) == self.REVIEW_STATUS:
                raise exceptions.StackDoesNotExist(stack.fqn)
            _old_template, old_params = self.get_stack_info(stack_details)
            old_template: Dict[str, Any] = parse_cloudformation_template(_old_template)
            change_type = "UPDATE"
        except exceptions.StackDoesNotExist:
            old_params: Dict[str, Union[List[str], str]] = {}
            old_template = {}
            change_type = "CREATE"

        changes, change_set_id = create_change_set(
            self.cloudformation,
            stack.fqn,
            template,
            parameters,
            tags,
            change_type,
            service_role=self.service_role,
        )
        new_parameters_as_dict = self.params_as_dict(
            [
                x
                if "ParameterValue" in x
                else {
                    "ParameterKey": x["ParameterKey"],  # type: ignore
                    "ParameterValue": old_params[x["ParameterKey"]],  # type: ignore
                }
                for x in parameters
            ]
        )
        params_diff = diff_parameters(old_params, new_parameters_as_dict)

        if changes or params_diff:
            with ui:
                if self.interactive:
                    output_summary(
                        stack.fqn,
                        "changes",
                        changes,
                        params_diff,
                        replacements_only=self.replacements_only,
                    )
                    output_full_changeset(
                        full_changeset=changes, params_diff=params_diff, fqn=stack.fqn
                    )
                else:
                    output_full_changeset(
                        full_changeset=changes,
                        params_diff=params_diff,
                        answer="y",
                        fqn=stack.fqn,
                    )

        self.cloudformation.delete_change_set(ChangeSetName=change_set_id)

        # ensure current stack outputs are loaded
        self.get_outputs(stack.fqn)

        # infer which outputs may have changed
        refs_to_invalidate: List[str] = []
        for change in changes:
            resc_change = change.get("ResourceChange", {})
            if resc_change.get("Type") == "Add":
                continue  # we don't care about anything new
            # scope of changes that can invalidate a change
            if (
                resc_change
                and (
                    resc_change.get("Replacement") == "True"
                    or "Properties" in resc_change.get("Scope", {})
                )
                and "LogicalResourceId" in resc_change
            ):
                LOGGER.debug(
                    "%s:added to invalidation list: %s",
                    stack.fqn,
                    resc_change["LogicalResourceId"],
                )
                refs_to_invalidate.append(resc_change["LogicalResourceId"])

        # invalidate cached outputs with inferred changes
        if "Outputs" in old_template:
            for output, props in old_template["Outputs"].items():
                if any(r in str(props["Value"]) for r in refs_to_invalidate):
                    self._outputs[stack.fqn].pop(output)
                    LOGGER.debug("%s:removed from the outputs: %s", output, stack.fqn)

        # push values for new + invalidated outputs to outputs
        for (
            output_name,
            output_params,
        ) in stack.blueprint.get_output_definitions().items():
            if output_name not in self._outputs[stack.fqn]:
                self._outputs[stack.fqn][
                    output_name
                ] = f"<inferred-change: {stack.fqn}.{output_name}={output_params['Value']}>"

        # when creating a changeset for a new stack, CFN creates a temporary
        # stack with a status of REVIEW_IN_PROGRESS. this is only removed if
        # the changeset is executed or it is manually deleted.
        if change_type == "CREATE":
            try:
                temp_stack = self.get_stack(stack.fqn)
                if self.is_stack_in_review(temp_stack):
                    LOGGER.debug(
                        "removing temporary stack that is created "
                        'with a ChangeSet of type "CREATE"'
                    )
                    # this method is currently only used by one action so
                    # hardcoding should be fine for now.
                    self.destroy_stack(temp_stack, action="diff")
            except exceptions.StackDoesNotExist:
                # not an issue if the stack was already cleaned up
                LOGGER.debug("%s:stack does not exist", stack.fqn)

        return self.get_outputs(stack.fqn)

    @staticmethod
    def params_as_dict(
        parameters_list: List[ParameterTypeDef],
    ) -> Dict[str, Union[List[str], str]]:
        """Parameters as dict."""
        return {
            param["ParameterKey"]: param["ParameterValue"]  # type: ignore
            for param in parameters_list
        }
