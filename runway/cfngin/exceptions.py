"""CFNgin exceptions."""


class CancelExecution(Exception):
    """Raised when we want to cancel executing the plan."""


class ChangesetDidNotStabilize(Exception):
    """Raised when the applying a changeset fails."""

    def __init__(self, change_set_id):
        """Instantiate class.

        Args:
            change_set_id (str): The changeset that failed.

        """
        self.id = change_set_id
        message = "Changeset '%s' did not reach a completed state." % (change_set_id)

        super().__init__(message)


class GraphError(Exception):
    """Raised when the graph is invalid (e.g. acyclic dependencies)."""

    def __init__(self, exception, stack, dependency):
        """Instantiate class.

        Args:
            exception (Exception): The exception that was raised by the invalid
                graph.
            stack (str): Name of the stack causing the error.
            dependency (str): Name of the dependency causing the error.

        """
        self.stack = stack
        self.dependency = dependency
        self.exception = exception
        message = "Error detected when adding '{}' as a dependency of '{}': {}".format(
            dependency, stack, str(exception),
        )
        super().__init__(message)


class ImproperlyConfigured(Exception):
    """Raised when a componenet is improperly configured."""

    def __init__(self, cls, error, *args, **kwargs):
        """Instantiate class.

        Args:
            cls (Any): The class that was improperly configured.
            error (Exception): The exception that was raised when trying to
                use cls.

        """
        message = 'Class "%s" is improperly configured: %s' % (cls, error,)
        super().__init__(message, *args, **kwargs)


class InvalidConfig(Exception):
    """Provided config file is invalid."""

    def __init__(self, errors):
        """Instantiate class.

        Args:
            errors (Union[str, List[Union[Exception, str]]]): Errors or error
                messages that are raised to identify that a config is invalid.

        """
        super().__init__(errors)
        self.errors = errors


class InvalidDockerizePipConfiguration(Exception):
    """Raised when the provided configuration for dockerized pip is invalid."""

    def __init__(self, msg):
        """Instantiate class.

        Args:
            msg (str): The reason for the error being raised.

        """
        self.message = msg
        super().__init__(self.message)


class InvalidUserdataPlaceholder(Exception):
    """Raised when a placeholder name in raw_user_data is not valid.

    E.g ``${100}`` would raise this.

    """

    def __init__(self, blueprint_name, exception_message, *args, **kwargs):
        """Instantiate class.

        Args:
            blueprint_name (str): Name of the blueprint with invalid userdata
                placeholder.
            exception_message (str): Message from the exception that was raised
                while parsing the userdata.

        """
        message = exception_message + ". "
        message += 'Could not parse userdata in blueprint "%s". ' % (blueprint_name)
        message += "Make sure to escape all $ symbols with a $$."
        super().__init__(message, *args, **kwargs)


class MissingEnvironment(Exception):
    """Raised when an environment lookup is used but the key doesn't exist."""

    def __init__(self, key, *args, **kwargs):
        """Instantiate class.

        Args:
            key (str): The key that was used but doesn't exist in the
            environment.

        """
        self.key = key
        message = "Environment missing key %s." % (key,)
        super().__init__(message, *args, **kwargs)


class MissingParameterException(Exception):
    """Raised if a required parameter with no default is missing."""

    def __init__(self, parameters, *args, **kwargs):
        """Instantiate class.

        Args:
            parameters (List[str]): A list of the parameters that are missing.

        """
        self.parameters = parameters
        message = "Missing required cloudformation parameters: %s" % (
            ", ".join(parameters),
        )
        super().__init__(message, *args, **kwargs)


class MissingVariable(Exception):
    """Raised when a variable with no default is not provided a value."""

    def __init__(self, blueprint_name, variable_name, *args, **kwargs):
        """Instantiate class.

        Args:
            blueprint_name (str): Name of the blueprint.
            variable_name (str): Name of the variable missing a value.

        """
        message = 'Variable "%s" in blueprint "%s" is missing' % (
            variable_name,
            blueprint_name,
        )
        super().__init__(message, *args, **kwargs)


class PipError(Exception):
    """Raised when pip returns a non-zero exit code."""

    def __init__(self):
        """Instantiate class."""
        self.message = (
            "A non-zero exit code was returned when invoking "
            "pip. More information can be found in the error above."
        )
        super().__init__(self.message)


class PipenvError(Exception):
    """Raised when pipenv returns a non-zero exit code."""

    def __init__(self):
        """Instantiate class."""
        self.message = (
            "A non-zero exit code was returned when invoking "
            "pipenv. Please ensure pipenv in installed and the "
            "Pipfile being used is valid. More information can be "
            "found in the error above."
        )
        super().__init__(self.message)


class PersistentGraphCannotLock(Exception):
    """Raised when the persistent graph in S3 cannot be locked."""

    def __init__(self, reason):
        """Instantiate class."""
        message = "Could not lock persistent graph; %s" % reason
        super().__init__(message)


class PersistentGraphCannotUnlock(Exception):
    """Raised when the persistent graph in S3 cannot be unlocked."""

    def __init__(self, reason):
        """Instantiate class."""
        message = "Could not unlock persistent graph; %s" % reason
        super().__init__(message)


class PersistentGraphLocked(Exception):
    """Raised when the persistent graph in S3 is lock.

    The action being executed requires it to be unlocked before attempted.

    """

    def __init__(self, message=None, reason=None):
        """Instantiate class."""
        if not message:
            message = "Persistant graph is locked. {}".format(
                reason
                or ("This action requires the graph to be unlocked to be executed.")
            )
        super().__init__(message)


class PersistentGraphLockCodeMissmatch(Exception):
    """Raised when the provided persistent graph lock code does not match.

    The code used to unlock the persistent graph must match the s3 object lock
    code.

    """

    def __init__(self, provided_code, s3_code):
        """Instantiate class."""
        message = (
            "The provided lock code '%s' does not match the S3 "
            "object lock code '%s'" % (provided_code, s3_code)
        )
        super().__init__(message)


class PersistentGraphUnlocked(Exception):
    """Raised when the persistent graph in S3 is unlock.

    The action being executed requires it to be locked before attempted.

    """

    def __init__(self, message=None, reason=None):
        """Instantiate class."""
        if not message:
            message = "Persistant graph is unlocked. {}".format(
                reason
                or ("This action requires the graph to be locked to be executed.")
            )
        super().__init__(message)


class PlanFailed(Exception):
    """Raised if any step of a plan fails."""

    def __init__(self, failed_steps, *args, **kwargs):
        """Instantiate class.

        Args:
            failed_steps (List[:class:`runway.cfngin.plan.Step`]): The steps
                that failed.

        """
        self.failed_steps = failed_steps

        step_names = ", ".join(step.name for step in failed_steps)
        message = "The following steps failed: %s" % (step_names,)

        super().__init__(message, *args, **kwargs)


class StackDidNotChange(Exception):
    """Raised when there are no changes to be made by the provider."""


class StackDoesNotExist(Exception):
    """Raised when a stack does not exist in AWS."""

    def __init__(self, stack_name, *args, **kwargs):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack that does not exist.

        """
        message = (
            'Stack: "%s" does not exist in outputs or the lookup is '
            "not available in this CFNgin run"
        ) % (stack_name,)
        super().__init__(message, *args, **kwargs)


class StackUpdateBadStatus(Exception):
    """Raised if the state of a stack can't be handled."""

    def __init__(self, stack_name, stack_status, reason, *args, **kwargs):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack.
            stack_status (str): The stack's status.
            reason (str): The reason for the current status.

        """
        self.stack_name = stack_name
        self.stack_status = stack_status

        message = (
            'Stack: "%s" cannot be updated nor re-created from state '
            "%s: %s" % (stack_name, stack_status, reason)
        )
        super().__init__(message, *args, **kwargs)


class StackFailed(Exception):
    """Raised when a stack action fails.

    Primarily used with hooks that act on stacks.

    """

    def __init__(self, stack_name, status_reason=None):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack.
            status_reason (str): The reason for the current status.

        """
        self.stack_name = stack_name
        self.status_reason = status_reason

        message = 'Stack "{}" failed'.format(stack_name)
        if status_reason:
            message += ' with reason "{}"'.format(status_reason)
        super().__init__(message)


class UnableToExecuteChangeSet(Exception):
    """Raised if changeset execution status is not ``AVAILABLE``."""

    def __init__(self, stack_name, change_set_id, execution_status):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack.
            change_set_id (str): The changeset that failed.
            execution_status (str): The value of the changeset's
                ``ExecutionStatus`` attribute.

        """
        self.stack_name = stack_name
        self.id = change_set_id
        self.execution_status = execution_status

        message = "Changeset '{}' on stack '{}' had bad execution status: {}".format(
            change_set_id, stack_name, execution_status,
        )

        super().__init__(message)


class UnhandledChangeSetStatus(Exception):
    """Raised when creating a changeset failed for an unhandled reason.

    Handled failure reasons include: no changes

    """

    def __init__(self, stack_name, change_set_id, status, status_reason):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack.
            change_set_id (str): The changeset that failed.
            status (str): The state that could not be handled.
            status_reason (str): Cause of the current state.

        """
        self.stack_name = stack_name
        self.id = change_set_id
        self.status = status
        self.status_reason = status_reason
        message = (
            "Changeset '%s' on stack '%s' returned an unhandled status "
            "'%s: %s'." % (change_set_id, stack_name, status, status_reason)
        )

        super().__init__(message)


class UnresolvedBlueprintVariable(Exception):  # TODO rename for blueprints only
    """Raised when trying to use a variable before it has been resolved."""

    def __init__(self, blueprint_name, variable, *args, **kwargs):
        """Instantiate class.

        Args:
            blueprint_name (str): Name of the blueprint that tried to use
                the unresolved variables.
            variable (:class:`runway.cfngin.variables.Variable`): The
                unresolved variable.

        """
        message = 'Variable "{}" in blueprint "{}" hasn\'t been resolved'.format(
            variable.name, blueprint_name,
        )
        super().__init__(message, *args, **kwargs)


class UnresolvedBlueprintVariables(Exception):  # TODO rename for blueprints only
    """Raised when trying to use variables before they has been resolved."""

    def __init__(self, blueprint_name, *args, **kwargs):
        """Instantiate class.

        Args:
            blueprint_name (str): Name of the blueprint that tried to use
                the unresolved variables.

        """
        message = "Blueprint: \"{}\" hasn't resolved it's variables".format(
            blueprint_name
        )
        super().__init__(message, *args, **kwargs)


class ValidatorError(Exception):
    """Used for errors raised by custom validators of blueprint variables."""

    def __init__(self, variable, validator, value, exception=None):
        """Instantiate class.

        Args:
            variable (str): The variable that failed validation.
            validator (str): The validator that was not passed.
            value (str): The value of the variable that did not pass the
                validator.
            exception (Exception): The exception raised by the validator.

        """
        self.variable = variable
        self.validator = validator
        self.value = value
        self.exception = exception
        self.message = "Validator '{}' failed for variable '{}' with value '{}'".format(
            self.validator, self.variable, self.value
        )

        if self.exception:
            self.message += ": %s: %s" % (
                self.exception.__class__.__name__,
                str(self.exception),
            )
        super().__init__()

    def __str__(self):
        """Return the exception's message when converting to a string."""
        return self.message


class VariableTypeRequired(Exception):
    """Raised when a variable defined in a blueprint is missing a type."""

    def __init__(self, blueprint_name, variable_name, *args, **kwargs):
        """Instantiate class.

        Args:
            blueprint_name (str): Name of the blueprint.
            variable_name (str): Name of the variable missing a type.

        """
        message = 'Variable "{}" in blueprint "{}" does not have a type'.format(
            variable_name, blueprint_name,
        )
        super().__init__(message, *args, **kwargs)
