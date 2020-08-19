"""Tests for runway.cfngin.providers.aws.default."""
# pylint: disable=too-many-lines
import copy
import os.path
import random
import string
import sys
import threading
import unittest
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, UnStubbedResponseError
from botocore.stub import Stubber
from mock import MagicMock, patch

from runway.cfngin import exceptions
from runway.cfngin.actions.diff import DictValue
from runway.cfngin.providers.aws import default
from runway.cfngin.providers.aws.default import (
    DEFAULT_CAPABILITIES,
    MAX_TAIL_RETRIES,
    Provider,
    ask_for_approval,
    create_change_set,
    generate_cloudformation_args,
    output_full_changeset,
    requires_replacement,
    summarize_params_diff,
    wait_till_change_set_complete,
)
from runway.cfngin.providers.base import Template
from runway.cfngin.session_cache import get_session
from runway.cfngin.stack import Stack
from runway.util import MutableMap

if sys.version_info.major < 3:
    from pathlib2 import Path  # pylint: disable=E
else:
    from pathlib import Path  # pylint: disable=E


def random_string(length=12):
    """Return a random string of variable length.

    Args:
        length (int): The # of characters to use in the random string.

    Returns:
        str: The random string.

    """
    return "".join([random.choice(string.ascii_letters) for _ in range(length)])


def generate_describe_stacks_stack(
    stack_name,
    creation_time=None,
    stack_status="CREATE_COMPLETE",
    tags=None,
    termination_protection=False,
):
    """Generate describe stacks stack."""
    tags = tags or []
    return {
        "StackName": stack_name,
        "StackId": stack_name,
        "CreationTime": creation_time or datetime(2015, 1, 1),
        "StackStatus": stack_status,
        "Tags": tags,
        "EnableTerminationProtection": termination_protection,
    }


def generate_get_template(file_name="cfn_template.json", stages_available=None):
    """Generate get template."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "../../fixtures")
    with open(os.path.join(fixture_dir, file_name), "r") as _file:
        return {
            "StagesAvailable": stages_available or ["Original"],
            "TemplateBody": _file.read(),
        }


def generate_stack_object(stack_name, outputs=None):
    """Generate stack object."""
    mock_stack = MagicMock(["name", "fqn", "blueprint"])
    if not outputs:
        outputs = {"FakeOutput": {"Value": {"Ref": "FakeResource"}}}
    mock_stack.name = stack_name
    mock_stack.fqn = stack_name
    mock_stack.blueprint = MagicMock(["get_output_definitions"])
    mock_stack.blueprint.get_output_definitions = MagicMock(return_value=outputs)
    return mock_stack


def generate_resource_change(replacement=True):
    """Generate resource change."""
    resource_change = {
        "Action": "Modify",
        "Details": [],
        "LogicalResourceId": "Fake",
        "PhysicalResourceId": "arn:aws:fake",
        "Replacement": "True" if replacement else "False",
        "ResourceType": "AWS::Fake",
        "Scope": ["Properties"],
    }
    return {
        "ResourceChange": resource_change,
        "Type": "Resource",
    }


def generate_change_set_response(
    status, execution_status="AVAILABLE", changes=None, status_reason="FAKE"
):
    """Generate change set response."""
    return {
        "ChangeSetName": "string",
        "ChangeSetId": "string",
        "StackId": "string",
        "StackName": "string",
        "Description": "string",
        "Parameters": [
            {
                "ParameterKey": "string",
                "ParameterValue": "string",
                "UsePreviousValue": False,
            },
        ],
        "CreationTime": datetime(2015, 1, 1),
        "ExecutionStatus": execution_status,
        "Status": status,
        "StatusReason": status_reason,
        "NotificationARNs": ["string"],
        "Capabilities": ["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        "Tags": [{"Key": "string", "Value": "string"}],
        "Changes": changes or [],
        "NextToken": "string",
    }


def generate_change(
    action="Modify",
    resource_type="EC2::Instance",
    replacement="False",
    requires_recreation="Never",
):
    """Generate a minimal change for a changeset."""
    return {
        "Type": "Resource",
        "ResourceChange": {
            "Action": action,
            "LogicalResourceId": random_string(),
            "PhysicalResourceId": random_string(),
            "ResourceType": resource_type,
            "Replacement": replacement,
            "Scope": ["Properties"],
            "Details": [
                {
                    "Target": {
                        "Attribute": "Properties",
                        "Name": random_string(),
                        "RequiresRecreation": requires_recreation,
                    },
                    "Evaluation": "Static",
                    "ChangeSource": "ResourceReference",
                    "CausingEntity": random_string(),
                },
            ],
        },
    }


class TestMethods(unittest.TestCase):
    """Tests for runway.cfngin.providers.aws.default."""

    def setUp(self):
        """Run before tests."""
        self.cfn = boto3.client("cloudformation")
        self.stubber = Stubber(self.cfn)

    def test_requires_replacement(self):
        """Test requires replacement."""
        changeset = [
            generate_resource_change(),
            generate_resource_change(replacement=False),
            generate_resource_change(),
        ]
        replacement = requires_replacement(changeset)
        self.assertEqual(len(replacement), 2)
        for resource in replacement:
            self.assertEqual(resource["ResourceChange"]["Replacement"], "True")

    def test_summarize_params_diff(self):
        """Test summarize params diff."""
        unmodified_param = DictValue("ParamA", "new-param-value", "new-param-value")
        modified_param = DictValue(
            "ParamB", "param-b-old-value", "param-b-new-value-delta"
        )
        added_param = DictValue("ParamC", None, "param-c-new-value")
        removed_param = DictValue("ParamD", "param-d-old-value", None)

        params_diff = [
            unmodified_param,
            modified_param,
            added_param,
            removed_param,
        ]
        self.assertEqual(summarize_params_diff([]), "")
        self.assertEqual(
            summarize_params_diff(params_diff),
            "\n".join(
                [
                    "Parameters Added: ParamC",
                    "Parameters Removed: ParamD",
                    "Parameters Modified: ParamB\n",
                ]
            ),
        )

        only_modified_params_diff = [modified_param]
        self.assertEqual(
            summarize_params_diff(only_modified_params_diff),
            "Parameters Modified: ParamB\n",
        )

        only_added_params_diff = [added_param]
        self.assertEqual(
            summarize_params_diff(only_added_params_diff), "Parameters Added: ParamC\n"
        )

        only_removed_params_diff = [removed_param]
        self.assertEqual(
            summarize_params_diff(only_removed_params_diff),
            "Parameters Removed: ParamD\n",
        )

    def test_ask_for_approval(self):
        """Test ask for approval."""
        get_input_path = "runway.cfngin.ui.get_raw_input"
        with patch(get_input_path, return_value="y"):
            self.assertIsNone(ask_for_approval([], [], None))

        for v in ("n", "N", "x", "\n"):
            with patch(get_input_path, return_value=v):
                with self.assertRaises(exceptions.CancelExecution):
                    ask_for_approval([], [])

        with patch(get_input_path, side_effect=["v", "n"]) as mock_get_input:
            with patch(
                "runway.cfngin.providers.aws.default.output_full_changeset"
            ) as mock_full_changeset:
                with self.assertRaises(exceptions.CancelExecution):
                    ask_for_approval([], [], True)
                self.assertEqual(mock_full_changeset.call_count, 1)
            self.assertEqual(mock_get_input.call_count, 2)

    def test_ask_for_approval_with_params_diff(self):
        """Test ask for approval with params diff."""
        get_input_path = "runway.cfngin.ui.get_raw_input"
        params_diff = [
            DictValue("ParamA", None, "new-param-value"),
            DictValue("ParamB", "param-b-old-value", "param-b-new-value-delta"),
        ]
        with patch(get_input_path, return_value="y"):
            self.assertIsNone(ask_for_approval([], params_diff, None))

        for v in ("n", "N", "x", "\n"):
            with patch(get_input_path, return_value=v):
                with self.assertRaises(exceptions.CancelExecution):
                    ask_for_approval([], params_diff)

        with patch(get_input_path, side_effect=["v", "n"]) as mock_get_input:
            with patch(
                "runway.cfngin.providers.aws.default.output_full_changeset"
            ) as mock_full_changeset:
                with self.assertRaises(exceptions.CancelExecution):
                    ask_for_approval([], params_diff, True)
                self.assertEqual(mock_full_changeset.call_count, 1)
            self.assertEqual(mock_get_input.call_count, 2)

    @patch("runway.cfngin.providers.aws.default.format_params_diff")
    @patch("runway.cfngin.providers.aws.default.yaml.safe_dump")
    def test_output_full_changeset(self, mock_safe_dump, patched_format):
        """Test output full changeset."""
        get_input_path = "runway.cfngin.ui.get_raw_input"

        safe_dump_counter = 0

        for v in ["y", "v", "Y", "V"]:
            with patch(get_input_path, return_value=v) as prompt:
                self.assertIsNone(
                    output_full_changeset(full_changeset=[], params_diff=[], fqn=None)
                )
                self.assertEqual(prompt.call_count, 1)
                safe_dump_counter += 1
                self.assertEqual(mock_safe_dump.call_count, safe_dump_counter)
                self.assertEqual(patched_format.call_count, 0)

        for v in ["n", "N"]:
            with patch(get_input_path, return_value=v) as prompt:
                output_full_changeset(
                    full_changeset=[], params_diff=[], answer=None, fqn=None
                )
                self.assertEqual(prompt.call_count, 1)
                self.assertEqual(mock_safe_dump.call_count, safe_dump_counter)
                self.assertEqual(patched_format.call_count, 0)

        with self.assertRaises(exceptions.CancelExecution):
            output_full_changeset(
                full_changeset=[], params_diff=[], answer="x", fqn=None
            )

        output_full_changeset(
            full_changeset=[], params_diff=["mock"], answer="y", fqn=None
        )
        safe_dump_counter += 1
        self.assertEqual(mock_safe_dump.call_count, safe_dump_counter)
        self.assertEqual(patched_format.call_count, 1)

    def test_wait_till_change_set_complete_success(self):
        """Test wait till change set complete success."""
        self.stubber.add_response(
            "describe_change_set", generate_change_set_response("CREATE_COMPLETE")
        )
        with self.stubber:
            wait_till_change_set_complete(self.cfn, "FAKEID")

        self.stubber.add_response(
            "describe_change_set", generate_change_set_response("FAILED")
        )
        with self.stubber:
            wait_till_change_set_complete(self.cfn, "FAKEID")

    def test_wait_till_change_set_complete_failed(self):
        """Test wait till change set complete failed."""
        # Need 2 responses for try_count
        for _ in range(2):
            self.stubber.add_response(
                "describe_change_set", generate_change_set_response("CREATE_PENDING")
            )
        with self.stubber:
            with self.assertRaises(exceptions.ChangesetDidNotStabilize):
                wait_till_change_set_complete(
                    self.cfn, "FAKEID", try_count=2, sleep_time=0.1
                )

    def test_create_change_set_stack_did_not_change(self):
        """Test create change set stack did not change."""
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )

        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                "FAILED", status_reason="Stack didn't contain changes."
            ),
        )

        self.stubber.add_response(
            "delete_change_set", {}, expected_params={"ChangeSetName": "CHANGESETID"}
        )

        with self.stubber:
            with self.assertRaises(exceptions.StackDidNotChange):
                create_change_set(
                    cfn_client=self.cfn,
                    fqn="my-fake-stack",
                    template=Template(url="http://fake.template.url.com/"),
                    parameters=[],
                    tags=[],
                )

    def test_create_change_set_unhandled_failed_status(self):
        """Test create change set unhandled failed status."""
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )

        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                "FAILED", status_reason="Some random bad thing."
            ),
        )

        with self.stubber:
            with self.assertRaises(exceptions.UnhandledChangeSetStatus):
                create_change_set(
                    cfn_client=self.cfn,
                    fqn="my-fake-stack",
                    template=Template(url="http://fake.template.url.com/"),
                    parameters=[],
                    tags=[],
                )

    def test_create_change_set_bad_execution_status(self):
        """Test create change set bad execution status."""
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )

        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="UNAVAILABLE",
            ),
        )

        with self.stubber:
            with self.assertRaises(exceptions.UnableToExecuteChangeSet):
                create_change_set(
                    cfn_client=self.cfn,
                    fqn="my-fake-stack",
                    template=Template(url="http://fake.template.url.com/"),
                    parameters=[],
                    tags=[],
                )

    def test_generate_cloudformation_args(self):
        """Test generate cloudformation args."""
        stack_name = "mystack"
        template_url = "http://fake.s3url.com/blah.json"
        template_body = '{"fake_body": "woot"}'
        std_args = {
            "stack_name": stack_name,
            "parameters": [],
            "tags": [],
            "template": Template(url=template_url),
        }
        std_return = {
            "StackName": stack_name,
            "Parameters": [],
            "Tags": [],
            "Capabilities": DEFAULT_CAPABILITIES,
            "TemplateURL": template_url,
        }
        result = generate_cloudformation_args(**std_args)
        self.assertEqual(result, std_return)

        result = generate_cloudformation_args(service_role="FakeRole", **std_args)
        service_role_result = copy.deepcopy(std_return)
        service_role_result["RoleARN"] = "FakeRole"
        self.assertEqual(result, service_role_result)

        result = generate_cloudformation_args(change_set_name="MyChanges", **std_args)
        change_set_result = copy.deepcopy(std_return)
        change_set_result["ChangeSetName"] = "MyChanges"
        self.assertEqual(result, change_set_result)

        # Check stack policy
        stack_policy = Template(body="{}")
        result = generate_cloudformation_args(stack_policy=stack_policy, **std_args)
        stack_policy_result = copy.deepcopy(std_return)
        stack_policy_result["StackPolicyBody"] = "{}"
        self.assertEqual(result, stack_policy_result)

        # If not TemplateURL is provided, use TemplateBody
        std_args["template"] = Template(body=template_body)
        template_body_result = copy.deepcopy(std_return)
        del template_body_result["TemplateURL"]
        template_body_result["TemplateBody"] = template_body
        result = generate_cloudformation_args(**std_args)
        self.assertEqual(result, template_body_result)


class TestProviderDefaultMode(unittest.TestCase):
    """Tests for runway.cfngin.providers.aws.default default mode."""

    def setUp(self):
        """Run before tests."""
        region = "us-east-1"
        self.session = get_session(region=region)
        self.provider = Provider(self.session, region=region, recreate_failed=False)
        self.stubber = Stubber(self.provider.cloudformation)

    def test_create_stack_no_changeset(self):
        """Test create_stack, no changeset, template url."""
        stack_name = "fake_stack"
        template = Template(url="http://fake.template.url.com/")
        parameters = []
        tags = []

        expected_args = generate_cloudformation_args(
            stack_name, parameters, tags, template
        )
        expected_args["EnableTerminationProtection"] = False

        self.stubber.add_response(
            "create_stack", {"StackId": stack_name}, expected_args
        )

        with self.stubber:
            self.provider.create_stack(stack_name, template, parameters, tags)
        self.stubber.assert_no_pending_responses()

    @patch("runway.cfngin.providers.aws.default.Provider.update_termination_protection")
    @patch("runway.cfngin.providers.aws.default.create_change_set")
    def test_create_stack_with_changeset(
        self, patched_create_change_set, patched_update_term
    ):
        """Test create_stack, force changeset, termination protection."""
        stack_name = "fake_stack"
        template_path = Path("./tests/unit/cfngin/fixtures/cfn_template.yaml")
        template = Template(body=template_path.read_text())
        parameters = []
        tags = []

        changeset_id = "CHANGESETID"

        patched_create_change_set.return_value = ([], changeset_id)

        self.stubber.add_response(
            "execute_change_set", {}, {"ChangeSetName": changeset_id}
        )

        with self.stubber:
            self.provider.create_stack(
                stack_name,
                template,
                parameters,
                tags,
                force_change_set=True,
                termination_protection=True,
            )
        self.stubber.assert_no_pending_responses()

        patched_create_change_set.assert_called_once_with(
            self.provider.cloudformation,
            stack_name,
            template,
            parameters,
            tags,
            "CREATE",
            service_role=self.provider.service_role,
        )
        patched_update_term.assert_called_once_with(stack_name, True)

    def test_destroy_stack(self):
        """Test destroy stack."""
        stack = {"StackName": "MockStack"}

        self.stubber.add_response("delete_stack", {}, stack)

        with self.stubber:
            self.assertIsNone(self.provider.destroy_stack(stack))
            self.stubber.assert_no_pending_responses()

    def test_get_stack_stack_does_not_exist(self):
        """Test get stack stack does not exist."""
        stack_name = "MockStack"
        self.stubber.add_client_error(
            "describe_stacks",
            service_error_code="ValidationError",
            service_message="Stack with id %s does not exist" % stack_name,
            expected_params={"StackName": stack_name},
        )

        with self.assertRaises(exceptions.StackDoesNotExist):
            with self.stubber:
                self.provider.get_stack(stack_name)

    def test_get_stack_stack_exists(self):
        """Test get stack stack exists."""
        stack_name = "MockStack"
        stack_response = {"Stacks": [generate_describe_stacks_stack(stack_name)]}
        self.stubber.add_response(
            "describe_stacks", stack_response, expected_params={"StackName": stack_name}
        )

        with self.stubber:
            response = self.provider.get_stack(stack_name)

        self.assertEqual(response["StackName"], stack_name)

    def test_select_destroy_method(self):
        """Test select destroy method."""
        for i in [
            [{"force_interactive": False}, self.provider.noninteractive_destroy_stack],
            [{"force_interactive": True}, self.provider.interactive_destroy_stack],
        ]:
            self.assertEqual(self.provider.select_destroy_method(**i[0]), i[1])

    def test_select_update_method(self):
        """Test select update method."""
        for i in [
            [
                {"force_interactive": True, "force_change_set": False},
                self.provider.interactive_update_stack,
            ],
            [
                {"force_interactive": False, "force_change_set": False},
                self.provider.default_update_stack,
            ],
            [
                {"force_interactive": False, "force_change_set": True},
                self.provider.noninteractive_changeset_update,
            ],
            [
                {"force_interactive": True, "force_change_set": True},
                self.provider.interactive_update_stack,
            ],
        ]:
            self.assertEqual(self.provider.select_update_method(**i[0]), i[1])

    def test_prepare_stack_for_update_completed(self):
        """Test prepare stack for update completed."""
        with self.stubber:
            stack_name = "MockStack"
            stack = generate_describe_stacks_stack(
                stack_name, stack_status="UPDATE_COMPLETE"
            )

            self.assertTrue(self.provider.prepare_stack_for_update(stack, []))

    def test_prepare_stack_for_update_in_progress(self):
        """Test prepare stack for update in progress."""
        stack_name = "MockStack"
        stack = generate_describe_stacks_stack(
            stack_name, stack_status="UPDATE_IN_PROGRESS"
        )

        with self.assertRaises(exceptions.StackUpdateBadStatus) as raised:
            with self.stubber:
                self.provider.prepare_stack_for_update(stack, [])

            self.assertIn("in-progress", str(raised.exception))

    def test_prepare_stack_for_update_non_recreatable(self):
        """Test prepare stack for update non recreatable."""
        stack_name = "MockStack"
        stack = generate_describe_stacks_stack(
            stack_name, stack_status="REVIEW_IN_PROGRESS"
        )

        with self.assertRaises(exceptions.StackUpdateBadStatus) as raised:
            with self.stubber:
                self.provider.prepare_stack_for_update(stack, [])

        self.assertIn("Unsupported state", str(raised.exception))

    def test_prepare_stack_for_update_disallowed(self):
        """Test prepare stack for update disallowed."""
        stack_name = "MockStack"
        stack = generate_describe_stacks_stack(
            stack_name, stack_status="ROLLBACK_COMPLETE"
        )

        with self.assertRaises(exceptions.StackUpdateBadStatus) as raised:
            with self.stubber:
                self.provider.prepare_stack_for_update(stack, [])

        self.assertIn("re-creation is disabled", str(raised.exception))
        # Ensure we point out to the user how to enable re-creation
        self.assertIn("--recreate-failed", str(raised.exception))

    def test_prepare_stack_for_update_bad_tags(self):
        """Test prepare stack for update bad tags."""
        stack_name = "MockStack"
        stack = generate_describe_stacks_stack(
            stack_name, stack_status="ROLLBACK_COMPLETE"
        )

        self.provider.recreate_failed = True

        with self.assertRaises(exceptions.StackUpdateBadStatus) as raised:
            with self.stubber:
                self.provider.prepare_stack_for_update(
                    stack, tags=[{"Key": "cfngin_namespace", "Value": "test"}]
                )

        self.assertIn("tags differ", str(raised.exception).lower())

    def test_prepare_stack_for_update_recreate(self):
        """Test prepare stack for update recreate."""
        stack_name = "MockStack"
        stack = generate_describe_stacks_stack(
            stack_name, stack_status="ROLLBACK_COMPLETE"
        )

        self.stubber.add_response(
            "delete_stack", {}, expected_params={"StackName": stack_name}
        )

        self.provider.recreate_failed = True

        with self.stubber:
            self.assertFalse(self.provider.prepare_stack_for_update(stack, []))

    def test_noninteractive_changeset_update_no_stack_policy(self):
        """Test noninteractive changeset update no stack policy."""
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )
        changes = [generate_change()]
        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )

        self.stubber.add_response("execute_change_set", {})

        with self.stubber:
            stack_name = "MockStack"
            self.provider.noninteractive_changeset_update(
                fqn=stack_name,
                template=Template(url="http://fake.template.url.com/"),
                old_parameters=[],
                parameters=[],
                stack_policy=None,
                tags=[],
            )

    def test_noninteractive_changeset_update_with_stack_policy(self):
        """Test noninteractive changeset update with stack policy."""
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )
        changes = [generate_change()]
        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )
        self.stubber.add_response("set_stack_policy", {})
        self.stubber.add_response("execute_change_set", {})

        with self.stubber:
            stack_name = "MockStack"
            self.provider.noninteractive_changeset_update(
                fqn=stack_name,
                template=Template(url="http://fake.template.url.com/"),
                old_parameters=[],
                parameters=[],
                stack_policy=Template(body="{}"),
                tags=[],
            )

    def test_noninteractive_destroy_stack_termination_protected(self):
        """Test noninteractive_destroy_stack with termination protection."""
        self.stubber.add_client_error("delete_stack")

        with self.stubber, self.assertRaises(ClientError):
            self.provider.noninteractive_destroy_stack("fake-stack")
        self.stubber.assert_no_pending_responses()

    @patch("runway.cfngin.providers.aws.default.output_full_changeset")
    def test_get_stack_changes_update(self, mock_output_full_cs):
        """Test get stack changes update."""
        stack_name = "MockStack"
        mock_stack = generate_stack_object(stack_name)

        self.stubber.add_response(
            "describe_stacks", {"Stacks": [generate_describe_stacks_stack(stack_name)]}
        )
        self.stubber.add_response(
            "get_template", generate_get_template("cfn_template.yaml")
        )
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": stack_name}
        )
        changes = [generate_change()]
        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )
        self.stubber.add_response("delete_change_set", {})
        self.stubber.add_response(
            "describe_stacks", {"Stacks": [generate_describe_stacks_stack(stack_name)]}
        )

        with self.stubber:
            result = self.provider.get_stack_changes(
                stack=mock_stack,
                template=Template(url="http://fake.template.url.com/"),
                parameters=[],
                tags=[],
            )

        mock_output_full_cs.assert_called_with(
            full_changeset=changes, params_diff=[], fqn=stack_name, answer="y"
        )
        expected_outputs = {
            "FakeOutput": "<inferred-change: MockStack.FakeOutput={}>".format(
                str({"Ref": "FakeResource"})
            )
        }
        self.assertEqual(self.provider.get_outputs(stack_name), expected_outputs)
        self.assertEqual(result, expected_outputs)

    @patch("runway.cfngin.providers.aws.default.output_full_changeset")
    def test_get_stack_changes_create(self, mock_output_full_cs):
        """Test get stack changes create."""
        stack_name = "MockStack"
        mock_stack = generate_stack_object(stack_name)

        self.stubber.add_response(
            "describe_stacks",
            {
                "Stacks": [
                    generate_describe_stacks_stack(
                        stack_name, stack_status="REVIEW_IN_PROGRESS"
                    )
                ]
            },
        )
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": stack_name}
        )
        changes = [generate_change()]
        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )
        self.stubber.add_response("delete_change_set", {})
        self.stubber.add_response(
            "describe_stacks",
            {
                "Stacks": [
                    generate_describe_stacks_stack(
                        stack_name, stack_status="REVIEW_IN_PROGRESS"
                    )
                ]
            },
        )
        self.stubber.add_response(
            "describe_stacks",
            {
                "Stacks": [
                    generate_describe_stacks_stack(
                        stack_name, stack_status="REVIEW_IN_PROGRESS"
                    )
                ]
            },
        )

        self.stubber.add_response("delete_stack", {})

        with self.stubber:
            self.provider.get_stack_changes(
                stack=mock_stack,
                template=Template(url="http://fake.template.url.com/"),
                parameters=[],
                tags=[],
            )

        mock_output_full_cs.assert_called_with(
            full_changeset=changes, params_diff=[], fqn=stack_name, answer="y"
        )

    def test_tail_stack_retry_on_missing_stack(self):
        """Test tail stack retry on missing stack."""
        stack_name = "SlowToCreateStack"
        stack = MagicMock(spec=Stack)
        stack.fqn = "my-namespace-{}".format(stack_name)

        default.TAIL_RETRY_SLEEP = 0.01

        # Ensure the stack never appears before we run out of retries
        for i in range(MAX_TAIL_RETRIES + 5):
            self.stubber.add_client_error(
                "describe_stack_events",
                service_error_code="ValidationError",
                service_message="Stack [{}] does not exist".format(stack_name),
                http_status_code=400,
                response_meta={"attempt": i + 1},
            )

        with self.stubber:
            try:
                self.provider.tail_stack(stack, threading.Event())
            except ClientError as exc:
                self.assertEqual(
                    exc.response["ResponseMetadata"]["attempt"], MAX_TAIL_RETRIES
                )

    def test_tail_stack_retry_on_missing_stack_eventual_success(self):
        """Test tail stack retry on missing stack eventual success."""
        stack_name = "SlowToCreateStack"
        stack = MagicMock(spec=Stack)
        stack.fqn = "my-namespace-{}".format(stack_name)

        default.TAIL_RETRY_SLEEP = 0.01
        default.GET_EVENTS_SLEEP = 0.01

        received_events = []

        def mock_log_func(event):
            received_events.append(event)

        def valid_event_response(stack, event_id):
            return {
                "StackEvents": [
                    {
                        "StackId": stack.fqn + "12345",
                        "EventId": event_id,
                        "StackName": stack.fqn,
                        "Timestamp": datetime.now(),
                    },
                ]
            }

        # Ensure the stack never appears before we run out of retries
        for i in range(3):
            self.stubber.add_client_error(
                "describe_stack_events",
                service_error_code="ValidationError",
                service_message="Stack [{}] does not exist".format(stack_name),
                http_status_code=400,
                response_meta={"attempt": i + 1},
            )

        self.stubber.add_response(
            "describe_stack_events", valid_event_response(stack, "InitialEvents")
        )

        self.stubber.add_response(
            "describe_stack_events", valid_event_response(stack, "Event1")
        )

        with self.stubber:
            try:
                self.provider.tail_stack(
                    stack, threading.Event(), log_func=mock_log_func
                )
            except UnStubbedResponseError:
                # Eventually we run out of responses - could not happen in
                # regular execution
                # normally this would just be dealt with when the threads were
                # shutdown, but doing so here is a little difficult because
                # we can't control the `tail_stack` loop
                pass

        self.assertEqual(received_events[0]["EventId"], "Event1")

    def test_update_termination_protection(self):
        """Test update_termination_protection."""
        stack_name = "fake-stack"
        test_cases = [
            MutableMap(aws=False, defined=True, expected=True),
            MutableMap(aws=True, defined=False, expected=False),
            MutableMap(aws=True, defined=True, expected=None),
            MutableMap(aws=False, defined=False, expected=None),
        ]

        for test in test_cases:
            self.stubber.add_response(
                "describe_stacks",
                {
                    "Stacks": [
                        generate_describe_stacks_stack(
                            stack_name, termination_protection=test.aws
                        )
                    ]
                },
                {"StackName": stack_name},
            )
            if isinstance(test.expected, bool):
                self.stubber.add_response(
                    "update_termination_protection",
                    {"StackId": stack_name},
                    {
                        "EnableTerminationProtection": test.expected,
                        "StackName": stack_name,
                    },
                )
            with self.stubber:
                self.provider.update_termination_protection(stack_name, test.defined)
            self.stubber.assert_no_pending_responses()


class TestProviderInteractiveMode(unittest.TestCase):
    """Tests for runway.cfngin.providers.aws.default interactive mode."""

    def setUp(self):
        """Run before tests."""
        region = "us-east-1"
        self.session = get_session(region=region)
        self.provider = Provider(self.session, interactive=True, recreate_failed=True)
        self.stubber = Stubber(self.provider.cloudformation)

    @patch("runway.cfngin.ui.get_raw_input")
    def test_interactive_destroy_stack(self, patched_input):
        """Test interactive_destroy_stack."""
        stack_name = "fake-stack"
        stack = {"StackName": stack_name}
        patched_input.return_value = "y"

        self.stubber.add_response("delete_stack", {}, stack)

        with self.stubber:
            self.assertIsNone(self.provider.interactive_destroy_stack(stack_name))
            self.stubber.assert_no_pending_responses()

    @patch("runway.cfngin.providers.aws.default.Provider.update_termination_protection")
    @patch("runway.cfngin.ui.get_raw_input")
    def test_interactive_destroy_stack_termination_protected(
        self, patched_input, patched_update_term
    ):
        """Test interactive_destroy_stack with termination protection."""
        stack_name = "fake-stack"
        stack = {"StackName": stack_name}
        patched_input.return_value = "y"

        self.stubber.add_client_error(
            "delete_stack", service_message="TerminationProtection"
        )
        self.stubber.add_response("delete_stack", {}, stack)

        with self.stubber:
            self.provider.interactive_destroy_stack(stack_name, approval="y")
        self.stubber.assert_no_pending_responses()
        patched_input.assert_called_once()
        patched_update_term.assert_called_once_with(stack_name, False)

    @patch("runway.cfngin.ui.get_raw_input")
    def test_destroy_stack_canceled(self, patched_input):
        """Test destroy stack canceled."""
        patched_input.return_value = "n"

        with self.assertRaises(exceptions.CancelExecution):
            stack = {"StackName": "MockStack"}
            self.provider.destroy_stack(stack)

    def test_successful_init(self):
        """Test successful init."""
        replacements = True
        provider = Provider(
            self.session, interactive=True, replacements_only=replacements
        )
        self.assertEqual(provider.replacements_only, replacements)

    @patch("runway.cfngin.providers.aws.default.Provider.update_termination_protection")
    @patch("runway.cfngin.providers.aws.default.ask_for_approval")
    def test_update_stack_execute_success_no_stack_policy(
        self, patched_approval, patched_update_term
    ):
        """Test update stack execute success no stack policy."""
        stack_name = "my-fake-stack"

        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )
        changes = [generate_change()]

        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )

        self.stubber.add_response("execute_change_set", {})

        with self.stubber:
            self.provider.update_stack(
                fqn=stack_name,
                template=Template(url="http://fake.template.url.com/"),
                old_parameters=[],
                parameters=[],
                tags=[],
            )

        patched_approval.assert_called_once_with(
            full_changeset=changes, params_diff=[], include_verbose=True, fqn=stack_name
        )
        patched_update_term.assert_called_once_with(stack_name, False)

    @patch("runway.cfngin.providers.aws.default.Provider.update_termination_protection")
    @patch("runway.cfngin.providers.aws.default.ask_for_approval")
    def test_update_stack_execute_success_with_stack_policy(
        self, patched_approval, patched_update_term
    ):
        """Test update stack execute success with stack policy."""
        stack_name = "my-fake-stack"

        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": "STACKID"}
        )
        changes = [generate_change()]

        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )

        self.stubber.add_response("set_stack_policy", {})

        self.stubber.add_response("execute_change_set", {})

        with self.stubber:
            self.provider.update_stack(
                fqn=stack_name,
                template=Template(url="http://fake.template.url.com/"),
                old_parameters=[],
                parameters=[],
                tags=[],
                stack_policy=Template(body="{}"),
            )

        patched_approval.assert_called_once_with(
            full_changeset=changes, params_diff=[], include_verbose=True, fqn=stack_name
        )
        patched_update_term.assert_called_once_with(stack_name, False)

    def test_select_destroy_method(self):
        """Test select destroy method."""
        for i in [
            [{"force_interactive": False}, self.provider.interactive_destroy_stack],
            [{"force_interactive": True}, self.provider.interactive_destroy_stack],
        ]:
            self.assertEqual(self.provider.select_destroy_method(**i[0]), i[1])

    def test_select_update_method(self):
        """Test select update method."""
        for i in [
            [
                {"force_interactive": False, "force_change_set": False},
                self.provider.interactive_update_stack,
            ],
            [
                {"force_interactive": True, "force_change_set": False},
                self.provider.interactive_update_stack,
            ],
            [
                {"force_interactive": False, "force_change_set": True},
                self.provider.interactive_update_stack,
            ],
            [
                {"force_interactive": True, "force_change_set": True},
                self.provider.interactive_update_stack,
            ],
        ]:
            self.assertEqual(self.provider.select_update_method(**i[0]), i[1])

    @patch("runway.cfngin.providers.aws.default.output_full_changeset")
    @patch("runway.cfngin.providers.aws.default.output_summary")
    def test_get_stack_changes_interactive(
        self, mock_output_summary, mock_output_full_cs
    ):
        """Test get stack changes interactive."""
        stack_name = "MockStack"
        mock_stack = generate_stack_object(stack_name)

        self.stubber.add_response(
            "describe_stacks", {"Stacks": [generate_describe_stacks_stack(stack_name)]}
        )
        self.stubber.add_response(
            "get_template", generate_get_template("cfn_template.yaml")
        )
        self.stubber.add_response(
            "create_change_set", {"Id": "CHANGESETID", "StackId": stack_name}
        )
        changes = [generate_change()]
        self.stubber.add_response(
            "describe_change_set",
            generate_change_set_response(
                status="CREATE_COMPLETE", execution_status="AVAILABLE", changes=changes,
            ),
        )
        self.stubber.add_response("delete_change_set", {})
        self.stubber.add_response(
            "describe_stacks", {"Stacks": [generate_describe_stacks_stack(stack_name)]}
        )

        with self.stubber:
            self.provider.get_stack_changes(
                stack=mock_stack,
                template=Template(url="http://fake.template.url.com/"),
                parameters=[],
                tags=[],
            )

        mock_output_summary.assert_called_with(
            stack_name, "changes", changes, [], replacements_only=False
        )
        mock_output_full_cs.assert_called_with(
            full_changeset=changes, params_diff=[], fqn=stack_name
        )
