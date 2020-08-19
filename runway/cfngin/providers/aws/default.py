"""Default AWS Provider."""
# pylint: disable=too-many-lines,too-many-public-methods
import json
import logging
import sys
import time
from threading import Lock  # thread safe, memoize, provider builder.

import botocore.exceptions
import yaml
from botocore.config import Config
from six.moves import urllib

from runway.util import DOC_SITE, JsonEncoder

from ... import exceptions
from ...actions.diff import DictValue, diff_parameters
from ...actions.diff import format_params_diff as format_diff
from ...session_cache import get_session
from ...ui import ui
from ...util import parse_cloudformation_template
from ..base import BaseProvider

LOGGER = logging.getLogger(__name__)

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


def get_cloudformation_client(session):
    """Get CloudFormaiton boto3 client."""
    config = Config(retries=dict(max_attempts=MAX_ATTEMPTS))
    return session.client("cloudformation", config=config)


def get_output_dict(stack):
    """Return a dict of key/values for the outputs for a given CF stack.

    Args:
        stack (Dict[str, Any]): The stack object to get
            outputs from.

    Returns:
        Dict[str, Any]: A dictionary with key/values for each output on the
        stack.

    """
    if not stack.get("Outputs"):
        return {}
    outputs = {
        output["OutputKey"]: output["OutputValue"]
        for output in stack.get("Outputs", [])
    }
    LOGGER.debug("%s stack outputs: %s", stack["StackName"], json.dumps(outputs))
    return outputs


def s3_fallback(
    fqn, template, parameters, tags, method, change_set_name=None, service_role=None
):
    """Falling back to legacy stacker S3 bucket region for templates."""
    LOGGER.warning(
        "falling back to deprecated, legacy stacker S3 bucket "
        "region for templates; to learn how to correctly provide an "
        "s3 bucket, visit %s/page/cfngin/configuration.html#s3-bucket",
        DOC_SITE,
    )
    # extra line break on purpose to avoid status updates removing URL
    # from view
    LOGGER.warning("\n")
    LOGGER.debug("modifying the S3 TemplateURL to point to us-east-1 endpoint")
    template_url = template.url
    template_url_parsed = urllib.parse.urlparse(template_url)
    template_url_parsed = template_url_parsed._replace(netloc="s3.amazonaws.com")
    template_url = urllib.parse.urlunparse(template_url_parsed)
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


def get_change_set_name():
    """Return a valid Change Set Name.

    The name has to satisfy the following regex::

        [a-zA-Z][-a-zA-Z0-9]*

    And must be unique across all change sets.

    """
    return "change-set-{}".format(int(time.time()))


def requires_replacement(changeset):
    """Return the changes within the changeset that require replacement.

    Args:
        changeset (list): List of changes

    Returns:
        list: A list of changes that require replacement, if any.

    """
    return [
        r for r in changeset if r["ResourceChange"].get("Replacement", False) == "True"
    ]


def output_full_changeset(full_changeset=None, params_diff=None, answer=None, fqn=None):
    """Optionally output full changeset.

    Args:
        full_changeset (Optional[List[Dict[str, Any]]]): A list of the full
            changeset that will be output if the user specifies verbose.
        params_diff (Optional[List[:class:`runway.cfngin.actions.diff.DictValue`):
            A list of DictValue detailing the differences between two
            parameters returned by
            :func:`runway.cfngin.actions.diff.diff_dictionaries`.
        answer (Optional[str]): predetermined answer to the prompt if it has
            already been answered or inferred.
        fqn (Optional[str]): fully qualified name of the stack.

    """
    if not answer:
        answer = ui.ask("Show full change set? [y/n] ").lower()
    if answer == "n":
        return
    if answer in ["y", "v"]:
        if fqn:
            msg = "%s full changeset" % (fqn)
        else:
            msg = "Full changeset"
        if params_diff:
            LOGGER.info(
                "%s:\n\n%s\n%s",
                msg,
                format_params_diff(params_diff),
                yaml.safe_dump(full_changeset),
            )
        else:
            LOGGER.info(
                "%s:\n%s", msg, yaml.safe_dump(full_changeset),
            )
        return
    raise exceptions.CancelExecution


def ask_for_approval(
    full_changeset=None, params_diff=None, include_verbose=False, fqn=None
):
    """Prompt the user for approval to execute a change set.

    Args:
        full_changeset (Optional[List[Dict[str, Any]]]): A list of the full
            changeset that will be output if the user specifies verbose.
        params_diff (Optional[List[:class:`runway.cfngin.actions.diff`]]):
            A list of DictValue detailing the differences between two
            parameters returned by
            :func:`runway.cfngin.actions.diff.diff_dictionaries`
        include_verbose (bool): Boolean for whether or not to include
            the verbose option.
        fqn (str): fully qualified name of the stack.

    Raises:
        CancelExecution: If approval no given.

    """
    approval_options = ["y", "n"]
    if include_verbose:
        approval_options.append("v")

    approve = ui.ask(
        "Execute the above changes? [{}] ".format("/".join(approval_options))
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


def output_summary(fqn, action, changeset, params_diff, replacements_only=False):
    """Log a summary of the changeset.

    Args:
        fqn (string): fully qualified name of the stack
        action (string): action to include in the log message
        changeset (list): AWS changeset
        params_diff (list): A list of dictionaries detailing the differences
            between two parameters returned by
            :func:`runway.cfngin.actions.diff.diff_dictionaries`
        replacements_only (bool, optional): boolean for whether or not we only
            want to list replacements

    """
    replacements = []
    changes = []
    for change in changeset:
        resource = change["ResourceChange"]
        replacement = resource.get("Replacement") == "True"
        summary = "- %s %s (%s)" % (
            resource["Action"],
            resource["LogicalResourceId"],
            resource["ResourceType"],
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
        summary += "Changes:\n%s" % ("\n".join(changes))
    LOGGER.info("%s %s:\n%s", fqn, action, summary)


def format_params_diff(params_diff):
    """Wrap :func:`runway.cfngin.actions.diff.format_params_diff` for testing."""
    return format_diff(params_diff)


def summarize_params_diff(params_diff):
    """Summarize parameter diff."""
    summary = ""

    added_summary = [v.key for v in params_diff if v.status() is DictValue.ADDED]
    if added_summary:
        summary += "Parameters Added: %s\n" % ", ".join(added_summary)

    removed_summary = [v.key for v in params_diff if v.status() is DictValue.REMOVED]
    if removed_summary:
        summary += "Parameters Removed: %s\n" % ", ".join(removed_summary)

    modified_summary = [v.key for v in params_diff if v.status() is DictValue.MODIFIED]
    if modified_summary:
        summary += "Parameters Modified: %s\n" % ", ".join(modified_summary)

    return summary


def wait_till_change_set_complete(
    cfn_client, change_set_id, try_count=25, sleep_time=0.5, max_sleep=3
):
    """Check state of a changeset, returning when it is in a complete state.

    Since changesets can take a little bit of time to get into a complete
    state, we need to poll it until it does so. This will try to get the
    state ``try_count`` times, waiting ``sleep_time`` * 2 seconds between each
    try up to the ``max_sleep`` number of seconds. If, after that time, the
    changeset is not in a complete state it fails. These default settings will
    wait a little over one minute.

    Args:
        cfn_client (:class:`botocore.client.Client`): Used to query
            CloudFormation.
        change_set_id (str): The unique changeset id to wait for.
        try_count (int): Number of times to try the call.
        sleep_time (int): Time to sleep between attempts.
        max_sleep (int): Max time to sleep during backoff

    Return:
        Dict[str, Any]: The response from CloudFormation for the
        ``describe_change_set`` call.

    """
    complete = False
    response = None
    for _ in range(try_count):
        response = cfn_client.describe_change_set(ChangeSetName=change_set_id,)
        complete = response["Status"] in ("FAILED", "CREATE_COMPLETE")
        if complete:
            break
        if sleep_time == max_sleep:
            LOGGER.debug("waiting on changeset for another %s seconds", sleep_time)
        time.sleep(sleep_time)

        # exponential backoff with max
        sleep_time = min(sleep_time * 2, max_sleep)
    if not complete:
        raise exceptions.ChangesetDidNotStabilize(change_set_id)
    return response


def create_change_set(
    cfn_client,
    fqn,
    template,
    parameters,
    tags,
    change_set_type="UPDATE",
    service_role=None,
):
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
            "didn't contain changes" in response["StatusReason"]
            or "No updates are to be performed" in status_reason
        ):
            LOGGER.debug(
                "%s:stack did not change; not updating and removing changeset", fqn,
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


def check_tags_contain(actual, expected):
    """Check if a set of AWS resource tags is contained in another.

    Every tag key in ``expected`` must be present in ``actual``, and have the
    same value. Extra keys in `actual` but not in ``expected`` are ignored.

    Args:
        actual (List[Dict[str, str]]): Set of tags to be verified, usually
            from the description of a resource. Each item must be a
            ``dict`` containing ``Key`` and ``Value`` items.
        expected (List[Dict[str, str]]): Set of tags that must be present in
            ``actual`` (in the same format).

    """
    actual_set = set((item["Key"], item["Value"]) for item in actual)
    expected_set = set((item["Key"], item["Value"]) for item in expected)

    return actual_set >= expected_set


def generate_cloudformation_args(
    stack_name,
    parameters,
    tags,
    template,
    capabilities=None,
    change_set_type=None,
    service_role=None,
    stack_policy=None,
    change_set_name=None,
):
    """Generate the args for common CloudFormation API interactions.

    This is used for ``create_stack``/``update_stack``/``create_change_set``
    calls in CloudFormation.

    Args:
        stack_name (str): The fully qualified stack name in Cloudformation.
        parameters (List[Dict[str, Any]]): A list of dictionaries that defines
            the parameter list to be applied to the Cloudformation stack.
        tags (List[Dict[str, str]]): A list of dictionaries that defines the
            tags that should be applied to the Cloudformation stack.
        template (:class:`runway.cfngin.provider.base.Template`): The template
            object.
        capabilities (Optional[List[str]]): A list of capabilities to use when
            updating Cloudformation.
        change_set_type (Optional[str]): An optional change set type to use
            with create_change_set.
        service_role (Optional[str]): An optional service role to use when
            interacting with Cloudformation.
        stack_policy (:class:`runway.cfngin.providers.base.Template`):
            A template object representing a stack policy.
        change_set_name (Optional[str]): An optional change set name to use
            with create_change_set.

    Returns:
        Dict[str, Any]: A dictionary of arguments to be used in the
        Cloudformation API call.

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
    else:
        args["TemplateBody"] = template.body

    # When creating args for CreateChangeSet, don't include the stack policy,
    # since ChangeSets don't support it.
    if not change_set_name:
        args.update(generate_stack_policy_args(stack_policy))

    return args


def generate_stack_policy_args(stack_policy=None):
    """Convert a stack policy object into keyword args.

    Args:
        stack_policy (:class:`runway.cfngin.providers.base.Template`):
            A template object representing a stack policy.

    Returns:
        dict: A dictionary of keyword arguments to be used elsewhere.

    """
    args = {}
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
        args["StackPolicyBody"] = stack_policy.body
    return args


class ProviderBuilder(object):  # pylint: disable=too-few-public-methods
    """Implements a Memorized ProviderBuilder for the AWS provider."""

    def __init__(self, region=None, **kwargs):
        """Instantiate class."""
        self.region = region
        self.kwargs = kwargs
        self.providers = {}
        self.lock = Lock()

    def build(self, region=None, profile=None):
        """Get or create the provider for the given region and profile."""
        with self.lock:
            # memorization lookup key derived from region + profile.
            key = "{}-{}".format(profile, region)
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
                    **self.kwargs
                )
                provider = self.providers[key]

        return provider


class Provider(BaseProvider):
    """AWS CloudFormation Provider."""

    DELETING_STATUS = "DELETE_IN_PROGRESS"

    DELETED_STATUS = "DELETE_COMPLETE"

    IN_PROGRESS_STATUSES = (
        "CREATE_IN_PROGRESS",
        "IMPORT_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
        "DELETE_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
    )

    ROLLING_BACK_STATUSES = (
        "ROLLBACK_IN_PROGRESS",
        "IMPORT_ROLLBACK_IN_PROGRESS",
        "UPDATE_ROLLBACK_IN_PROGRESS",
    )

    FAILED_STATUSES = (
        "CREATE_FAILED",
        "ROLLBACK_FAILED",
        "ROLLBACK_COMPLETE",
        "DELETE_FAILED",
        "IMPORT_ROLLBACK_FAILED",
        "UPDATE_ROLLBACK_FAILED",
        # Note: UPDATE_ROLLBACK_COMPLETE is in both the FAILED and COMPLETE
        # sets, because we need to wait for it when a rollback is triggered,
        # but still mark the stack as failed.
        "UPDATE_ROLLBACK_COMPLETE",
    )

    COMPLETE_STATUSES = (
        "CREATE_COMPLETE",
        "DELETE_COMPLETE",
        "IMPORT_COMPLETE",
        "UPDATE_COMPLETE",
        "IMPORT_ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_COMPLETE",
    )

    RECREATION_STATUSES = ("CREATE_FAILED", "ROLLBACK_FAILED", "ROLLBACK_COMPLETE")

    REVIEW_STATUS = "REVIEW_IN_PROGRESS"

    def __init__(
        self,
        session,
        region=None,
        interactive=False,
        replacements_only=False,
        recreate_failed=False,
        service_role=None,
    ):
        """Instantiate class."""
        self._outputs = {}
        self.region = region
        self.cloudformation = get_cloudformation_client(session)
        self.interactive = interactive
        # replacements only is only used in interactive mode
        self.replacements_only = interactive and replacements_only
        self.recreate_failed = interactive or recreate_failed
        self.service_role = service_role

    def get_stack(self, stack_name, *args, **kwargs):  # pylint: disable=unused-argument
        """Get stack."""
        try:
            return self.cloudformation.describe_stacks(StackName=stack_name)["Stacks"][
                0
            ]
        except botocore.exceptions.ClientError as err:
            if "does not exist" not in str(err):
                raise
            raise exceptions.StackDoesNotExist(stack_name)

    def get_stack_status(  # pylint: disable=unused-argument
        self, stack, *args, **kwargs
    ):
        """Get stack status."""
        return stack["StackStatus"]

    def is_stack_being_destroyed(  # pylint: disable=unused-argument
        self, stack, **kwargs
    ):
        """Whether the status of the stack indicates it is 'being destroyed'."""
        return self.get_stack_status(stack) == self.DELETING_STATUS

    def is_stack_completed(self, stack):
        """Whether the status of the stack indicates it is 'complete'."""
        return self.get_stack_status(stack) in self.COMPLETE_STATUSES

    def is_stack_in_progress(self, stack):
        """Whether the status of the stack indicates it is 'in progress'."""
        return self.get_stack_status(stack) in self.IN_PROGRESS_STATUSES

    def is_stack_destroyed(self, stack):
        """Whether the status of the stack indicates it is 'deleted'."""
        return self.get_stack_status(stack) == self.DELETED_STATUS

    def is_stack_recreatable(self, stack):
        """Whether the status of the stack indicates it is 'recreating'."""
        return self.get_stack_status(stack) in self.RECREATION_STATUSES

    def is_stack_rolling_back(self, stack):
        """Whether the status of the stack indicates it is 'rolling back'."""
        return self.get_stack_status(stack) in self.ROLLING_BACK_STATUSES

    def is_stack_failed(self, stack):
        """Whether the status of the stack indicates it is 'failed'."""
        return self.get_stack_status(stack) in self.FAILED_STATUSES

    def is_stack_in_review(self, stack):
        """Whether the status of the stack indicates if 'review in progress'."""
        return self.get_stack_status(stack) == self.REVIEW_STATUS

    def tail_stack(self, stack, cancel, action=None, log_func=None, retries=None):
        """Tail the events of a stack."""

        def _log_func(event):
            template = "[%s] %s %s %s"
            event_args = [
                event["LogicalResourceId"],
                event["ResourceType"],
                event["ResourceStatus"],
            ]
            if event.get("ResourceStatusReason"):
                template += " (%s)"
                event_args.append(event["ResourceStatusReason"])
            LOGGER.verbose(template, *([stack.fqn] + event_args))

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
    def _tail_print(event):
        print(
            "%s %s %s"
            % (event["ResourceStatus"], event["ResourceType"], event["EventId"])
        )

    def get_events(self, stack_name, chronological=True):
        """Get the events in batches and return in chronological order."""
        next_token = None
        event_list = []
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
            return reversed(sum(event_list, []))
        return sum(event_list, [])

    def get_rollback_status_reason(self, stack_name):
        """Process events and returns latest roll back reason."""
        event = next(
            (
                item
                for item in self.get_events(stack_name, False)
                if item["ResourceStatus"] == "UPDATE_ROLLBACK_IN_PROGRESS"
            ),
            None,
        )
        if event:
            reason = event["ResourceStatusReason"]
            return reason
        event = next(
            (
                item
                for item in self.get_events(stack_name)
                if item["ResourceStatus"] == "ROLLBACK_IN_PROGRESS"
            ),
            None,
        )
        reason = event["ResourceStatusReason"]
        return reason

    def tail(
        self,
        stack_name,
        cancel,
        log_func=_tail_print,
        sleep_time=5,
        include_initial=True,
    ):
        """Show and then tail the event log."""
        # First dump the full list of events in chronological order and keep
        # track of the events we've seen already
        seen = set()
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

    def destroy_stack(self, stack, *args, **kwargs):  # pylint: disable=unused-argument
        """Destroy a CloudFormation Stack.

        Args:
            stack (:class:`stacker.stack.Stack`): Stack to be destroyed.

        Keyword Args:
            action (str): Name of the action being executed. This impacts
                the log message used.
            approval (Optional[str]): Response to approval prompt.
            force_interactive (bool): Always ask for approval.

        """
        action = kwargs.pop("action", "destroy")
        approval = kwargs.pop("approval", None)
        force_interactive = kwargs.pop("force_interactive", False)
        fqn = self.get_stack_name(stack)
        LOGGER.debug("%s:attempting to delete stack", fqn)

        if action == "build":
            LOGGER.info(
                "%s:removed from the CFNgin config file; it is being destroyed", fqn
            )

        destroy_method = self.select_destroy_method(force_interactive)
        return destroy_method(fqn=fqn, action=action, approval=approval, **kwargs)

    def create_stack(  # pylint: disable=arguments-differ
        self,
        fqn,
        template,
        parameters,
        tags,
        force_change_set=False,
        stack_policy=None,
        termination_protection=False,
        **kwargs
    ):
        """Create a new Cloudformation stack.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to use when creating the stack.
            parameters (list): A list of dictionaries that defines the
                parameter list to be applied to the Cloudformation stack.
            tags (list): A list of dictionaries that defines the tags
                that should be applied to the Cloudformation stack.
            force_change_set (bool): Whether or not to force change set use.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.
            termination_protection (bool): End state of the stack's termination
                protection.

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
                **kwargs
            )

            self.cloudformation.execute_change_set(ChangeSetName=change_set_id,)
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
            # this arg is only valid for stack creation so its not part of
            # generate_cloudformation_args.
            args["EnableTerminationProtection"] = termination_protection

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

    def select_update_method(self, force_interactive, force_change_set):
        """Select the correct update method when updating a stack.

        Args:
            force_interactive (str): Whether or not to force interactive mode
                no matter what mode the provider is in.
            force_change_set (bool): Whether or not to force change set use.

        Returns:
            function: The correct object method to use when updating.

        """
        if self.interactive or force_interactive:
            return self.interactive_update_stack
        if force_change_set:
            return self.noninteractive_changeset_update
        return self.default_update_stack

    def prepare_stack_for_update(self, stack, tags):
        """Prepare a stack for updating.

        It may involve deleting the stack if is has failed it's initial
        creation. The deletion is only allowed if:

        - The stack contains all the tags configured in the current context;
        - The stack is in one of the statuses considered safe to re-create
        - ``recreate_failed`` is enabled, due to either being explicitly
          enabled by the user, or because interactive mode is on.

        Args:
            stack (dict): a stack object returned from get_stack
            tags (list): list of expected tags that must be present in the
                stack if it must be re-created

        Returns:
            bool: True if the stack can be updated, False if it must be
            re-created

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
                'The "%s" stack is in a failed state (%s).\n'
                "It cannot be updated, but it can be deleted and re-created.\n"
                "All its current resources will IRREVERSIBLY DESTROYED.\n"
                "Proceed carefully!\n\n" % (stack_name, stack_status)
            )
            sys.stdout.flush()

            ask_for_approval(include_verbose=False, fqn=stack_name)

        LOGGER.warning("%s:destroying stack for re-creation", stack_name)
        self.destroy_stack(stack, approval="y")

        return False

    def update_stack(  # pylint: disable=arguments-differ
        self,
        fqn,
        template,
        old_parameters,
        parameters,
        tags,
        force_interactive=False,
        force_change_set=False,
        stack_policy=None,
        termination_protection=False,
        **kwargs
    ):
        """Update a Cloudformation stack.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to use when updating the stack.
            old_parameters (List[Dict[str, Any]]): A list of dictionaries that
                defines the parameter list on the existing Cloudformation
                stack.
            parameters (List[Dict[str, Any]]): A list of dictionaries that
                defines the parameter list to be applied to the Cloudformation
                stack.
            tags (List[Dict[str, str]]): A list of dictionaries that defines
                the tags that should be applied to the Cloudformation stack.
            force_interactive (bool): A flag that indicates whether the update
                should be interactive. If set to True, interactive mode will
                be used no matter if the provider is in interactive mode or
                not. False will follow the behavior of the provider.
            force_change_set (bool): A flag that indicates whether the update
                must be executed with a change set.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.
            termination_protection (bool): End state of the stack's termination
                protection.

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
            **kwargs
        )

    def update_termination_protection(self, fqn, termination_protection):
        """Update a Stack's termination protection if needed.

        Runs before the normal stack update process.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            termination_protection (bool): End state of the stack's termination
                protection.

        """
        stack = self.get_stack(fqn)

        if stack["EnableTerminationProtection"] != termination_protection:
            LOGGER.debug(
                '%s:updating termination protection of stack to "%s"',
                fqn,
                termination_protection,
            )
            self.cloudformation.update_termination_protection(
                EnableTerminationProtection=termination_protection, StackName=fqn
            )

    def deal_with_changeset_stack_policy(self, fqn, stack_policy):
        """Set a stack policy when using changesets.

        ChangeSets don't allow you to set stack policies in the same call to
        update them. This sets it before executing the changeset if the
        stack policy is passed in.

        Args:
            fqn (str): Fully qualified name of the stack.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.

        """
        if stack_policy:
            kwargs = generate_stack_policy_args(stack_policy)
            kwargs["StackName"] = fqn
            LOGGER.debug("%s:adding stack policy", fqn)
            self.cloudformation.set_stack_policy(**kwargs)

    def interactive_destroy_stack(self, fqn, approval=None, **kwargs):
        """Delete a CloudFormation stack in interactive mode.

        Args:
            fqn (str): A fully qualified stack name.
            approval (Optional[str]): Response to approval prompt.

        """
        LOGGER.debug("%s:using interactive provider mode", fqn)
        action = kwargs.get("action", "destroy")

        approval_options = ["y", "n"]
        try:
            ui.lock()
            approval = (
                approval
                or ui.ask(
                    "Destroy {description}stack '{fqn}'{detail}? [{opts}] ".format(
                        description="temporary " if action == "diff" else "",
                        fqn=fqn,
                        detail=" created to generate a change set"
                        if action == "diff"
                        else "",
                        opts="/".join(approval_options),
                    )
                ).lower()
            )
        finally:
            ui.unlock()

        if approval != "y":
            raise exceptions.CancelExecution

        try:
            return self.noninteractive_destroy_stack(fqn, **kwargs)
        except botocore.exceptions.ClientError as err:
            if "TerminationProtection" in err.response["Error"]["Message"]:
                approval = ui.ask(
                    "Termination protection is enabled for "
                    "stack '{}'.\nWould you like to disable it "
                    "and try destroying the stack again? "
                    "[{}] ".format(fqn, "/".join(approval_options))
                ).lower()
                if approval == "y":
                    self.update_termination_protection(fqn, False)
                    return self.noninteractive_destroy_stack(fqn, **kwargs)
            raise

    def interactive_update_stack(
        self, fqn, template, old_parameters, parameters, stack_policy, tags
    ):
        """Update a Cloudformation stack in interactive mode.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to use when updating the stack.
            old_parameters (List[Dict[str, Any]]): A list of dictionaries that
                defines the parameter list on the existing Cloudformation stack.
            parameters (List[Dict[str, Any]]): A list of dictionaries that
                defines the parameter list to be applied to the Cloudformation
                stack.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.
            tags (List[Dict[str, str]]): A list of dictionaries that defines
                the tags that should be applied to the Cloudformation stack.

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
                    "ParameterKey": x["ParameterKey"],
                    "ParameterValue": old_parameters_as_dict[x["ParameterKey"]],
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
            ui.lock()
            try:
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
            finally:
                ui.unlock()

        self.deal_with_changeset_stack_policy(fqn, stack_policy)

        self.cloudformation.execute_change_set(ChangeSetName=change_set_id,)

    def noninteractive_destroy_stack(  # pylint: disable=unused-argument
        self, fqn, **kwargs
    ):
        """Delete a CloudFormation stack without interaction.

        Args:
            fqn (str): A fully qualified stack name.

        """
        LOGGER.debug("%s:destroying stack", fqn)
        args = {"StackName": fqn}
        if self.service_role:
            args["RoleARN"] = self.service_role

        self.cloudformation.delete_stack(**args)

    def noninteractive_changeset_update(  # pylint: disable=unused-argument
        self, fqn, template, old_parameters, parameters, stack_policy, tags,
    ):
        """Update a Cloudformation stack using a change set.

        This is required for stacks with a defined Transform (i.e. SAM), as the
        default ``update_stack`` API cannot be used with them.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to use when updating the stack.
            old_parameters (list): A list of dictionaries that defines the
                parameter list on the existing Cloudformation stack.
            parameters (list): A list of dictionaries that defines the
                parameter list to be applied to the Cloudformation stack.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.
            tags (list): A list of dictionaries that defines the tags
                that should be applied to the Cloudformation stack.

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

        self.cloudformation.execute_change_set(ChangeSetName=change_set_id,)

    def select_destroy_method(self, force_interactive):
        """Select the correct destroy method for destroying a stack.

        Args:
            force_interactive (bool): Always ask for approval.

        Returns:
            Interactive or non-interactive method to be invoked.

        """
        if self.interactive or force_interactive:
            return self.interactive_destroy_stack
        return self.noninteractive_destroy_stack

    def default_update_stack(  # pylint: disable=unused-argument
        self, fqn, template, old_parameters, parameters, tags, stack_policy=None,
    ):
        """Update a Cloudformation stack in default mode.

        Args:
            fqn (str): The fully qualified name of the Cloudformation stack.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to use when updating the stack.
            old_parameters (list): A list of dictionaries that defines the
                parameter list on the existing Cloudformation stack.
            parameters (list): A list of dictionaries that defines the
                parameter list to be applied to the Cloudformation stack.
            tags (list): A list of dictionaries that defines the tags
                that should be applied to the Cloudformation stack.
            stack_policy (:class:`runway.cfngin.providers.base.Template`):
                A template object representing a stack policy.

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
    def get_stack_name(stack):
        """Get stack name."""
        return stack["StackName"]

    @staticmethod
    def get_stack_tags(stack):
        """Get stack tags."""
        return stack["Tags"]

    def get_outputs(self, stack_name, *args, **kwargs):
        """Get stack outputs."""
        if not self._outputs.get(stack_name):
            stack = self.get_stack(stack_name)
            self._outputs[stack_name] = get_output_dict(stack)
        return self._outputs[stack_name]

    @staticmethod
    def get_output_dict(stack):
        """Get stack outputs dict."""
        return get_output_dict(stack)

    def get_stack_info(self, stack):
        """Get the template and parameters of the stack currently in AWS.

        Returns:
            Tuple[str, Dict[str, Any]]

        """
        stack_name = stack["StackId"]

        try:
            template = self.cloudformation.get_template(StackName=stack_name)[
                "TemplateBody"
            ]
        except botocore.exceptions.ClientError as err:
            if "does not exist" not in str(err):
                raise
            raise exceptions.StackDoesNotExist(stack_name)

        parameters = self.params_as_dict(stack.get("Parameters", []))

        if isinstance(template, str):  # handle yaml templates
            template = parse_cloudformation_template(template)

        return json.dumps(template, cls=JsonEncoder), parameters

    def get_stack_changes(self, stack, template, parameters, tags):
        """Get the changes from a ChangeSet.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): The stack to get
                changes.
            template (:class:`runway.cfngin.providers.base.Template`):
                A Template object to compaired to.
            parameters (List[Dict[str, Any]]): A list of dictionaries that
                defines the parameter list to be applied to the Cloudformation
                stack.
            tags (List[Dict[str, Any]]): A list of dictionaries that defines
                the tags that should be applied to the Cloudformation stack.

        Returns:
            Dict[str, Any]: Stack outputs with inferred changes.

        """
        try:
            stack_details = self.get_stack(stack.fqn)
            # handling for orphaned changeset temp stacks
            if self.get_stack_status(stack_details) == self.REVIEW_STATUS:
                raise exceptions.StackDoesNotExist(stack.fqn)
            _old_template, old_params = self.get_stack_info(stack_details)
            old_template = parse_cloudformation_template(_old_template)
            change_type = "UPDATE"
        except exceptions.StackDoesNotExist:
            old_params = {}
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
                    "ParameterKey": x["ParameterKey"],
                    "ParameterValue": old_params[x["ParameterKey"]],
                }
                for x in parameters
            ]
        )
        params_diff = diff_parameters(old_params, new_parameters_as_dict)

        if changes or params_diff:
            ui.lock()
            try:
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
            finally:
                ui.unlock()

        self.cloudformation.delete_change_set(ChangeSetName=change_set_id)

        # ensure current stack outputs are loaded
        self.get_outputs(stack.fqn)

        # infer which outputs may have changed
        refs_to_invalidate = []
        for change in changes:
            resc_change = change.get("ResourceChange", {})
            if resc_change.get("Type") == "Add":
                continue  # we don't care about anything new
            # scope of changes that can invalidate a change
            if resc_change and (
                resc_change.get("Replacement") == "True"
                or "Properties" in resc_change["Scope"]
            ):
                LOGGER.debug(
                    "%s:added to invalidation list: %s",
                    stack.fqn,
                    resc_change["LogicalResourceId"],
                )
                refs_to_invalidate.append(resc_change["LogicalResourceId"])

        # invalidate cached outputs with inferred changes
        for output, props in old_template.get("Outputs", {}).items():
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
                ] = "<inferred-change: {}.{}={}>".format(
                    stack.fqn, output_name, str(output_params["Value"])
                )

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
    def params_as_dict(parameters_list):
        """Parameters as dict."""
        parameters = dict()
        for param in parameters_list:
            parameters[param["ParameterKey"]] = param["ParameterValue"]
        return parameters
