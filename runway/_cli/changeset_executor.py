"""Execute CloudFormation changesets."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import boto3
from botocore.exceptions import ClientError, WaiterError

if TYPE_CHECKING:
    from mypy_boto3_cloudformation.client import CloudFormationClient

    from ..context import RunwayContext
    from .._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


class ChangesetExecutionError(Exception):
    """Error during changeset execution."""

    def __init__(self, stack_name: str, changeset_id: str, reason: str) -> None:
        """Initialize error.

        Args:
            stack_name: Name of the stack.
            changeset_id: Changeset ARN or ID.
            reason: Reason for failure.

        """
        self.stack_name = stack_name
        self.changeset_id = changeset_id
        self.reason = reason
        super().__init__(
            f"Failed to execute changeset '{changeset_id}' on stack '{stack_name}': {reason}"
        )


class ChangesetExecutor:
    """Execute pre-created CloudFormation changesets."""

    def __init__(self, ctx: RunwayContext) -> None:
        """Initialize executor.

        Args:
            ctx: Runway context with AWS credentials/region.

        """
        self.ctx = ctx
        self._session = boto3.Session(region_name=ctx.env.aws_region)
        self._cfn: CloudFormationClient = self._session.client("cloudformation")

    def execute(self, stack_fqn: str, changeset_id: str) -> None:
        """Execute a single changeset.

        Args:
            stack_fqn: Fully qualified stack name.
            changeset_id: Changeset ARN or name.

        Raises:
            ChangesetExecutionError: If execution fails.

        """
        LOGGER.info("%s:executing changeset %s", stack_fqn, changeset_id)

        try:
            # Verify changeset exists and is executable
            response = self._cfn.describe_change_set(ChangeSetName=changeset_id)
            status = response.get("Status", "")
            execution_status = response.get("ExecutionStatus", "")

            if status != "CREATE_COMPLETE":
                raise ChangesetExecutionError(
                    stack_fqn,
                    changeset_id,
                    f"Changeset status is '{status}', expected 'CREATE_COMPLETE'",
                )

            if execution_status != "AVAILABLE":
                if execution_status in ("EXECUTE_COMPLETE", "EXECUTE_IN_PROGRESS"):
                    raise ChangesetExecutionError(
                        stack_fqn,
                        changeset_id,
                        f"Changeset has already been executed (status: {execution_status})",
                    )
                if execution_status == "UNAVAILABLE":
                    raise ChangesetExecutionError(
                        stack_fqn,
                        changeset_id,
                        "Changeset is unavailable - it may have been deleted or expired",
                    )
                if execution_status == "OBSOLETE":
                    raise ChangesetExecutionError(
                        stack_fqn,
                        changeset_id,
                        "Changeset is obsolete - a newer changeset exists for this stack",
                    )
                raise ChangesetExecutionError(
                    stack_fqn,
                    changeset_id,
                    f"Execution status is '{execution_status}', expected 'AVAILABLE'",
                )

            # Execute the changeset
            self._cfn.execute_change_set(ChangeSetName=changeset_id)

            # Determine if this is CREATE or UPDATE
            change_type = response.get("ChangeSetType", "UPDATE")

            # Wait for completion
            self._wait_for_stack(stack_fqn, change_type)

            LOGGER.success("%s:changeset execution complete", stack_fqn)

        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            error_msg = err.response.get("Error", {}).get("Message", str(err))

            if error_code == "ChangeSetNotFound":
                raise ChangesetExecutionError(
                    stack_fqn,
                    changeset_id,
                    "Changeset not found - it may have expired or been deleted",
                ) from err

            raise ChangesetExecutionError(stack_fqn, changeset_id, error_msg) from err

    def _wait_for_stack(
        self, stack_name: str, change_type: str, timeout: int = 3600
    ) -> None:
        """Wait for stack operation to complete.

        Args:
            stack_name: Name of the stack.
            change_type: Type of change (CREATE or UPDATE).
            timeout: Maximum seconds to wait.

        Raises:
            ChangesetExecutionError: If wait times out or stack fails.

        """
        waiter_name = (
            "stack_create_complete" if change_type == "CREATE" else "stack_update_complete"
        )
        waiter = self._cfn.get_waiter(waiter_name)

        try:
            LOGGER.info("%s:waiting for stack %s to complete...", stack_name, change_type.lower())
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={"Delay": 10, "MaxAttempts": timeout // 10},
            )
        except WaiterError as err:
            # Get stack events for debugging
            try:
                events = self._cfn.describe_stack_events(StackName=stack_name)
                failed_events = [
                    e
                    for e in events.get("StackEvents", [])
                    if "FAILED" in e.get("ResourceStatus", "")
                ]
                if failed_events:
                    latest_failure = failed_events[0]
                    reason = latest_failure.get("ResourceStatusReason", "Unknown error")
                    raise ChangesetExecutionError(
                        stack_name, "", f"Stack operation failed: {reason}"
                    ) from err
            except ClientError:
                pass  # Ignore errors when fetching events

            raise ChangesetExecutionError(
                stack_name, "", f"Stack operation timed out or failed: {err}"
            ) from err


def execute_changesets_from_file(
    ctx: RunwayContext,
    changeset_file: str,
    stack_filter: tuple[str, ...] | None = None,
) -> None:
    """Execute changesets from a JSON file.

    Args:
        ctx: Runway context.
        changeset_file: Path to JSON file with changeset info.
        stack_filter: Optional tuple of stack names to filter (only execute these).

    Raises:
        ChangesetExecutionError: If execution fails.

    """
    # Load changeset file
    file_path = Path(changeset_file)
    if not file_path.exists():
        raise FileNotFoundError(f"Changeset file not found: {changeset_file}")

    try:
        with file_path.open() as f:
            changeset_data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON in changeset file '{changeset_file}': {err}") from err

    changesets = changeset_data.get("changesets", [])
    if not changesets:
        LOGGER.warning("No changesets found in file: %s", changeset_file)
        return

    # Execute each changeset
    executor = ChangesetExecutor(ctx)
    executed_count = 0
    skipped_count = 0

    for cs_info in changesets:
        stack_fqn = cs_info.get("stack", "")
        changeset_id = cs_info.get("changeset_id", "")

        if not stack_fqn or not changeset_id:
            LOGGER.warning("Invalid changeset entry (missing stack or changeset_id): %s", cs_info)
            continue

        # Check if this stack is targeted (if --stack option used)
        if stack_filter:
            if not any(stack_fqn.endswith(s) or s in stack_fqn for s in stack_filter):
                LOGGER.debug("Skipping %s (not in --stack filter)", stack_fqn)
                skipped_count += 1
                continue

        executor.execute(stack_fqn, changeset_id)
        executed_count += 1

    if executed_count == 0 and skipped_count > 0:
        LOGGER.warning(
            "No changesets executed - all %d changesets were filtered out by --stack option",
            skipped_count,
        )
    elif executed_count == 0:
        LOGGER.warning("No changesets were executed")
    else:
        LOGGER.info(
            "Changeset execution complete: %d executed, %d skipped",
            executed_count,
            skipped_count,
        )
