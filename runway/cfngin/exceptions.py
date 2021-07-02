"""CFNgin exceptions."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

from ..exceptions import RunwayError

if TYPE_CHECKING:
    from ..type_defs import AnyPath
    from ..variables import Variable
    from .plan import Step


class CfnginError(RunwayError):
    """Base class for custom exceptions raised by Runway."""

    message: str


class CancelExecution(CfnginError):
    """Raised when we want to cancel executing the plan."""

    message: str = "Plan canceled"


class CfnginBucketAccessDenied(CfnginError):
    """Access denied to CFNgin bucket.

    This can occur when the bucket exists in another AWS account and/or the
    credentials being used do not have adequate permissions to access the bucket.

    """

    bucket_name: str
    message: str

    def __init__(self, *, bucket_name: str) -> None:
        """Instantiate class.

        Args:
            bucket_name: Name of the CFNgin bucket.

        """
        self.bucket_name = bucket_name
        self.message = f"access denied for cfngin_bucket {bucket_name}"
        super().__init__()


class CfnginBucketNotFound(CfnginError):
    """CFNgin bucket specified or default bucket being used but it does not exist.

    This can occur when using a custom stack to deploy the CFNgin bucket but the
    custom stack does not create bucket that is expected.

    """

    bucket_name: str
    message: str

    def __init__(self, *, bucket_name: str) -> None:
        """Instantiate class.

        Args:
            bucket_name: Name of the CFNgin bucket.

        """
        self.bucket_name = bucket_name
        self.message = f"cfngin_bucket does not exist {bucket_name}"
        super().__init__()


class CfnginBucketRequired(CfnginError):
    """CFNgin bucket is required to use a feature but it not provided/disabled."""

    config_path: Optional[Path]
    message: str

    def __init__(
        self, *, config_path: Optional[AnyPath] = None, reason: Optional[str] = None
    ) -> None:
        """Instantiate class.

        Args:
            config_path: Path to the CFNgin config file.
            reason: Reason why CFNgin bucket is needed.

        """
        self.message = "cfngin_bucket is required"
        if reason:
            self.message += f"; {reason}"
        if isinstance(config_path, str):
            config_path = Path(config_path)
        if config_path:
            self.message += f" ({config_path})"
        self.config_path = config_path
        super().__init__()


class ChangesetDidNotStabilize(CfnginError):
    """Raised when the applying a changeset fails."""

    message: str

    def __init__(self, change_set_id: str) -> None:
        """Instantiate class.

        Args:
            change_set_id: The changeset that failed.

        """
        self.id = change_set_id
        self.message = f"Changeset '{change_set_id}' did not reach a completed state."
        super().__init__()


class GraphError(CfnginError):
    """Raised when the graph is invalid (e.g. acyclic dependencies)."""

    message: str

    def __init__(self, exception: Exception, stack: str, dependency: str) -> None:
        """Instantiate class.

        Args:
            exception: The exception that was raised by the invalid
                graph.
            stack: Name of the stack causing the error.
            dependency: Name of the dependency causing the error.

        """
        self.stack = stack
        self.dependency = dependency
        self.exception = exception
        self.message = (
            f"Error detected when adding '{dependency}' "
            f"as a dependency of '{stack}': {exception}"
        )
        super().__init__()


class ImproperlyConfigured(CfnginError):
    """Raised when a componenet is improperly configured."""

    message: str

    def __init__(self, kls: Any, error: Exception, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            kls: The class that was improperly configured.
            error: The exception that was raised when trying to use cls.

        """
        self.message = f'Class "{kls}" is improperly configured: {error}'
        super().__init__(*args, **kwargs)


class InvalidConfig(CfnginError):
    """Provided config file is invalid."""

    errors: Union[str, List[Union[Exception, str]]]
    message: str

    def __init__(self, errors: Union[str, List[Union[Exception, str]]]) -> None:
        """Instantiate class.

        Args:
            errors: Errors or error messages that are raised to identify that a
                config is invalid.

        """
        self.errors = errors
        if isinstance(errors, list):
            self.message = "\n".join(str(e) for e in errors)
        else:
            self.message = errors
        super().__init__(errors)


class InvalidDockerizePipConfiguration(CfnginError):
    """Raised when the provided configuration for dockerized pip is invalid."""

    message: str

    def __init__(self, msg: str) -> None:
        """Instantiate class.

        Args:
            msg: The reason for the error being raised.

        """
        self.message = msg
        super().__init__()


class InvalidUserdataPlaceholder(CfnginError):
    """Raised when a placeholder name in raw_user_data is not valid.

    E.g ``${100}`` would raise this.

    """

    message: str

    def __init__(
        self, blueprint_name: str, exception_message: str, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            blueprint_name: Name of the blueprint with invalid userdata placeholder.
            exception_message: Message from the exception that was raised while
                parsing the userdata.

        """
        self.message = (
            f'{exception_message}. Could not parse userdata in blueprint {blueprint_name}". '
            "Make sure to escape all $ symbols with a $$."
        )
        super().__init__(*args, **kwargs)


class MissingEnvironment(CfnginError):
    """Raised when an environment lookup is used but the key doesn't exist."""

    message: str

    def __init__(self, key: str, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            key: The key that was used but doesn't exist in the environment.

        """
        self.key = key
        self.message = f"Environment missing key {key}."
        super().__init__(*args, **kwargs)


class MissingParameterException(CfnginError):
    """Raised if a required parameter with no default is missing."""

    message: str

    def __init__(self, parameters: List[str], *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            parameters: A list of the parameters that are missing.

        """
        self.parameters = parameters
        self.message = (
            f"Missing required cloudformation parameters: {', '.join(parameters)}"
        )
        super().__init__(*args, **kwargs)


class MissingVariable(CfnginError):
    """Raised when a variable with no default is not provided a value."""

    message: str

    def __init__(
        self, blueprint_name: str, variable_name: str, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            blueprint_name: Name of the blueprint.
            variable_name: Name of the variable missing a value.

        """
        self.message = (
            f'Variable "{variable_name}" in blueprint "{blueprint_name}" is missing'
        )
        super().__init__(*args, **kwargs)


class PipError(CfnginError):
    """Raised when pip returns a non-zero exit code."""

    message: str

    def __init__(self) -> None:
        """Instantiate class."""
        self.message = (
            "A non-zero exit code was returned when invoking "
            "pip. More information can be found in the error above."
        )
        super().__init__()


class PipenvError(CfnginError):
    """Raised when pipenv returns a non-zero exit code."""

    message: str

    def __init__(self) -> None:
        """Instantiate class."""
        self.message = (
            "A non-zero exit code was returned when invoking "
            "pipenv. Please ensure pipenv in installed and the "
            "Pipfile being used is valid. More information can be "
            "found in the error above."
        )
        super().__init__()


class PersistentGraphCannotLock(CfnginError):
    """Raised when the persistent graph in S3 cannot be locked."""

    message: str

    def __init__(self, reason: str) -> None:
        """Instantiate class."""
        self.message = f"Could not lock persistent graph; {reason}"
        super().__init__()


class PersistentGraphCannotUnlock(CfnginError):
    """Raised when the persistent graph in S3 cannot be unlocked."""

    message: str

    def __init__(self, reason: Union[Exception, str]) -> None:
        """Instantiate class."""
        self.message = f"Could not unlock persistent graph; {reason}"
        super().__init__()


class PersistentGraphLocked(CfnginError):
    """Raised when the persistent graph in S3 is lock.

    The action being executed requires it to be unlocked before attempted.

    """

    message: str

    def __init__(
        self, *, message: Optional[str] = None, reason: Optional[str] = None
    ) -> None:
        """Instantiate class."""
        if message:
            self.message = message
        else:
            reason = (
                reason
                or "This action requires the graph to be unlocked to be executed."
            )
            self.message = f"Persistant graph is locked. {reason}"
        super().__init__()


class PersistentGraphLockCodeMissmatch(CfnginError):
    """Raised when the provided persistent graph lock code does not match.

    The code used to unlock the persistent graph must match the s3 object lock
    code.

    """

    message: str

    def __init__(self, provided_code: str, s3_code: Optional[str]) -> None:
        """Instantiate class."""
        self.message = (
            f"The provided lock code '{provided_code}' does not match the S3 "
            f"object lock code '{s3_code}'"
        )
        super().__init__()


class PersistentGraphUnlocked(CfnginError):
    """Raised when the persistent graph in S3 is unlock.

    The action being executed requires it to be locked before attempted.

    """

    message: str

    def __init__(
        self, message: Optional[str] = None, reason: Optional[str] = None
    ) -> None:
        """Instantiate class."""
        if message:
            self.message = message
        else:
            reason = (
                reason or "This action requires the graph to be locked to be executed."
            )
            self.message = f"Persistant graph is unlocked. {reason}"
        super().__init__()


class PlanFailed(CfnginError):
    """Raised if any step of a plan fails."""

    message: str

    def __init__(self, failed_steps: List[Step], *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            failed_steps: The steps that failed.

        """
        self.failed_steps = failed_steps

        step_names = ", ".join(step.name for step in failed_steps)
        self.message = f"The following steps failed: {step_names}"

        super().__init__(*args, **kwargs)


class StackDidNotChange(CfnginError):
    """Raised when there are no changes to be made by the provider."""

    message: str = "Stack did not change"


class StackDoesNotExist(CfnginError):
    """Raised when a stack does not exist in AWS."""

    message: str

    def __init__(self, stack_name: str, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack that does not exist.

        """
        self.message = (
            f'Stack: "{stack_name}" does not exist in outputs or the lookup is '
            "not available in this CFNgin run"
        )
        super().__init__(*args, **kwargs)


class StackUpdateBadStatus(CfnginError):
    """Raised if the state of a stack can't be handled."""

    message: str

    def __init__(
        self, stack_name: str, stack_status: str, reason: str, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack.
            stack_status: The stack's status.
            reason: The reason for the current status.

        """
        self.stack_name = stack_name
        self.stack_status = stack_status

        self.message = (
            f'Stack: "{stack_name}" cannot be updated nor re-created from state '
            f"{stack_status}: {reason}"
        )
        super().__init__(*args, **kwargs)


class StackFailed(CfnginError):
    """Raised when a stack action fails.

    Primarily used with hooks that act on stacks.

    """

    message: str

    def __init__(self, stack_name: str, status_reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack.
            status_reason: The reason for the current status.

        """
        self.stack_name = stack_name
        self.status_reason = status_reason

        self.message = f'Stack "{stack_name}" failed'
        if status_reason:
            self.message += f' with reason "{status_reason}"'
        super().__init__()


class UnableToExecuteChangeSet(CfnginError):
    """Raised if changeset execution status is not ``AVAILABLE``."""

    message: str

    def __init__(
        self, stack_name: str, change_set_id: str, execution_status: str
    ) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack.
            change_set_id: The changeset that failed.
            execution_status: The value of the changeset's ``ExecutionStatus``
                attribute.

        """
        self.stack_name = stack_name
        self.id = change_set_id
        self.execution_status = execution_status

        self.message = (
            f"Changeset '{change_set_id}' on stack '{stack_name}' had bad "
            f"execution status: {execution_status}"
        )

        super().__init__()


class UnhandledChangeSetStatus(CfnginError):
    """Raised when creating a changeset failed for an unhandled reason.

    Handled failure reasons include: no changes

    """

    message: str

    def __init__(
        self, stack_name: str, change_set_id: str, status: str, status_reason: str
    ) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack.
            change_set_id: The changeset that failed.
            status: The state that could not be handled.
            status_reason: Cause of the current state.

        """
        self.stack_name = stack_name
        self.id = change_set_id
        self.status = status
        self.status_reason = status_reason
        self.message = (
            f"Changeset '{change_set_id}' on stack '{stack_name}' returned an unhandled status "
            f"'{status}: {status_reason}'."
        )

        super().__init__()


class UnresolvedBlueprintVariable(CfnginError):
    """Raised when trying to use a variable before it has been resolved."""

    message: str

    def __init__(
        self, blueprint_name: str, variable: Variable, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            blueprint_name: Name of the blueprint that tried to use
                the unresolved variables.
            variable: The unresolved variable.

        """
        self.message = (
            f'Variable "{variable.name}" in blueprint "{blueprint_name}" '
            "hasn't been resolved"
        )
        super().__init__(*args, **kwargs)


class UnresolvedBlueprintVariables(CfnginError):
    """Raised when trying to use variables before they has been resolved."""

    message: str

    def __init__(self, blueprint_name: str, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            blueprint_name: Name of the blueprint that tried to use the unresolved
                variables.

        """
        self.message = f"Blueprint: \"{blueprint_name}\" hasn't resolved it's variables"
        super().__init__(*args, **kwargs)


class ValidatorError(CfnginError):
    """Used for errors raised by custom validators of blueprint variables."""

    message: str

    def __init__(
        self,
        variable: str,
        validator: str,
        value: str,
        exception: Optional[Exception] = None,
    ) -> None:
        """Instantiate class.

        Args:
            variable: The variable that failed validation.
            validator: The validator that was not passed.
            value: The value of the variable that did not pass the validator.
            exception: The exception raised by the validator.

        """
        self.variable = variable
        self.validator = validator
        self.value = value
        self.exception = exception
        self.message = (
            f"Validator '{self.validator}' failed for variable '{self.variable}' "
            f"with value '{self.value}'"
        )

        if self.exception:
            self.message += (
                f": {self.exception.__class__.__name__}: {str(self.exception)}"
            )
        super().__init__()

    def __str__(self):
        """Return the exception's message when converting to a string."""
        return self.message


class VariableTypeRequired(CfnginError):
    """Raised when a variable defined in a blueprint is missing a type."""

    message: str

    def __init__(
        self, blueprint_name: str, variable_name: str, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            blueprint_name: Name of the blueprint.
            variable_name: Name of the variable missing a type.

        """
        self.message = (
            f'Variable "{variable_name}" in blueprint "{blueprint_name}" '
            "does not have a type"
        )
        super().__init__(*args, **kwargs)
