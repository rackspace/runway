"""CFNgin diff action."""
from __future__ import annotations

import logging
import sys
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from botocore.exceptions import ClientError

from ...core.providers.aws.s3 import Bucket
from .. import exceptions
from ..status import (
    COMPLETE,
    INTERRUPTED,
    DoesNotExistInCloudFormation,
    NotSubmittedStatus,
    NotUpdatedStatus,
    SkippedStatus,
)
from . import deploy
from .base import build_walker

if TYPE_CHECKING:
    from ..._logging import RunwayLogger
    from ..stack import Stack
    from ..status import Status

_NV = TypeVar("_NV")
_OV = TypeVar("_OV")

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class DictValue(Generic[_OV, _NV]):
    """Used to create a diff of two dictionaries."""

    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNMODIFIED = "UNMODIFIED"

    formatter = "%s%s = %s"

    def __init__(self, key: str, old_value: _OV, new_value: _NV) -> None:
        """Instantiate class."""
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    def __eq__(self, other: object) -> bool:
        """Compare if self is equal to another object."""
        return self.__dict__ == other.__dict__

    def changes(self) -> List[str]:
        """Return changes to represent the diff between old and new value.

        Returns:
            Representation of the change (if any) between old and new value.

        """
        output: List[str] = []
        if self.status() is self.UNMODIFIED:
            output = [self.formatter % (" ", self.key, self.old_value)]
        elif self.status() is self.ADDED:
            output.append(self.formatter % ("+", self.key, self.new_value))
        elif self.status() is self.REMOVED:
            output.append(self.formatter % ("-", self.key, self.old_value))
        elif self.status() is self.MODIFIED:
            output.append(self.formatter % ("-", self.key, self.old_value))
            output.append(self.formatter % ("+", self.key, self.new_value))
        return output

    def status(self) -> str:
        """Status of changes between the old value and new value."""
        if self.old_value == self.new_value:
            return self.UNMODIFIED
        if self.old_value is None:
            return self.ADDED
        if self.new_value is None:
            return self.REMOVED
        return self.MODIFIED


def diff_dictionaries(
    old_dict: Dict[str, _OV], new_dict: Dict[str, _NV]
) -> Tuple[int, List[DictValue[_OV, _NV]]]:
    """Calculate the diff two single dimension dictionaries.

    Args:
        old_dict: Old dictionary.
        new_dict: New dictionary.

    Returns:
        Number of changed records and the :class:`DictValue` object containing
        the changes.

    """
    old_set = set(old_dict)
    new_set = set(new_dict)

    added_set = new_set - old_set
    removed_set = old_set - new_set
    common_set = old_set & new_set

    changes = 0
    output: List[DictValue[Any, Any]] = []
    for key in added_set:
        changes += 1
        output.append(DictValue(key, None, new_dict[key]))

    for key in removed_set:
        changes += 1
        output.append(DictValue(key, old_dict[key], None))

    for key in common_set:
        output.append(DictValue(key, old_dict[key], new_dict[key]))
        if str(old_dict[key]) != str(new_dict[key]):
            changes += 1

    output.sort(key=attrgetter("key"))
    return changes, output


def format_params_diff(parameter_diff: List[DictValue[Any, Any]]) -> str:
    """Handle the formatting of differences in parameters.

    Args:
        parameter_diff: A list of :class:`DictValue` detailing the differences
            between two dicts returned by :func:`diff_dictionaries`.

    Returns:
        A formatted string that represents a parameter diff

    """
    params_output = "\n".join(line for v in parameter_diff for line in v.changes())
    return (
        """--- Old Parameters
+++ New Parameters
******************
%s\n"""
        % params_output
    )


def diff_parameters(
    old_params: Dict[str, _OV], new_params: Dict[str, _NV]
) -> List[DictValue[_OV, _NV]]:
    """Compare the old vs. new parameters and returns a "diff".

    If there are no changes, we return an empty list.

    Args:
        old_params: old paramters
        new_params: new parameters

    Returns:
        A list of differences.

    """
    changes, diff = diff_dictionaries(old_params, new_params)
    if changes == 0:
        return []
    return diff


class Action(deploy.Action):
    """Responsible for diffing CloudFormation stacks in AWS and locally.

    Generates the deploy plan based on stack dependencies (these dependencies
    are determined automatically based on references to output values from
    other stacks).

    The plan is then used to create a changeset for a stack using a
    generated template based on the current config.

    """

    DESCRIPTION = "Diff stacks"
    NAME = "diff"

    @property
    def _stack_action(self) -> Callable[..., Status]:
        """Run against a step."""
        return self._diff_stack

    def _diff_stack(  # pylint: disable=too-many-return-statements
        self, stack: Stack, **_: Any
    ) -> Status:
        """Handle diffing a stack in CloudFormation vs our config."""
        if self.cancel.wait(0):
            return INTERRUPTED

        if not deploy.should_submit(stack):
            return NotSubmittedStatus()

        provider = self.build_provider()

        if not deploy.should_update(stack):
            stack.set_outputs(provider.get_outputs(stack.fqn))
            return NotUpdatedStatus()

        tags = deploy.build_stack_tags(stack)

        try:
            stack.resolve(self.context, provider)
            parameters = self.build_parameters(stack)
            outputs = provider.get_stack_changes(
                stack, self._template(stack.blueprint), parameters, tags
            )
            stack.set_outputs(outputs)
        except exceptions.StackDidNotChange:
            LOGGER.info("%s:no changes", stack.fqn)
            stack.set_outputs(provider.get_outputs(stack.fqn))
        except exceptions.StackDoesNotExist:
            if self.context.persistent_graph:
                return SkippedStatus(
                    "persistent graph: stack does not exist, will be removed"
                )
            return DoesNotExistInCloudFormation()
        except AttributeError as err:
            if (
                self.context.persistent_graph
                and "defined class or template path" in str(err)
            ):
                return SkippedStatus("persistent graph: will be destroyed")
            raise
        except ClientError as err:
            if (
                err.response["Error"]["Code"] == "ValidationError"
                and "length less than or equal to" in err.response["Error"]["Message"]
            ):
                LOGGER.error(
                    "%s:template is too large to provide directly to the API; "
                    "S3 must be used",
                    stack.name,
                )
                return SkippedStatus("cfngin_bucket: existing bucket required")
            raise
        return COMPLETE

    def run(
        self,
        *,
        concurrency: int = 0,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        force: bool = False,  # pylint: disable=unused-argument
        outline: bool = False,  # pylint: disable=unused-argument
        tail: bool = False,  # pylint: disable=unused-argument
        upload_disabled: bool = False,  # pylint: disable=unused-argument
        **_kwargs: Any,
    ) -> None:
        """Kicks off the diffing of the stacks in the stack_definitions."""
        plan = self._generate_plan(
            require_unlocked=False, include_persistent_graph=True
        )
        plan.outline(logging.DEBUG)
        if plan.keys():
            LOGGER.info("diffing stacks: %s", ", ".join(plan.keys()))
        else:
            LOGGER.warning("no stacks detected (error in config?)")
        walker = build_walker(concurrency)
        plan.execute(walker)

    def pre_run(
        self,
        *,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        outline: bool = False,  # pylint: disable=unused-argument
        **__kwargs: Any,
    ) -> None:
        """Any steps that need to be taken prior to running the action.

        Handle CFNgin bucket access denied & not existing.

        """
        if not self.bucket_name:
            return
        bucket = Bucket(self.context, self.bucket_name, self.bucket_region)
        if bucket.forbidden:
            LOGGER.error("access denied for CFNgin bucket: %s", bucket.name)
            sys.exit(1)
        if bucket.not_found:
            LOGGER.warning(
                'cfngin_bucket "%s" does not exist and will be creating '
                "during the next deploy",
                bucket.name,
            )
            LOGGER.verbose("proceeding without a cfngin_bucket...")
            self.bucket_name = None

    def post_run(
        self,
        *,
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        outline: bool = False,  # pylint: disable=unused-argument
        **__kwargs: Any,
    ) -> None:
        """Do nothing."""
