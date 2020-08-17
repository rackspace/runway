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

        super(ChangesetDidNotStabilize, self).__init__(message)


class FailedLookup(Exception):
    """Intermediary Exception to be converted to FailedVariableLookup.

    Should be caught by error handling and
    :class:`runway.cfngin.exceptions.FailedVariableLookup` raised instead to
    construct a propper error message.

    """

    def __init__(self, lookup, error, *args, **kwargs):
        """Instantiate class.

        Args:
            lookup (:class:`runway.cfngin.variables.VariableValueLookup`):
                Attempted lookup and resulted in an exception being raised.
            error (Exception): The exception that was raised.

        """
        self.lookup = lookup
        self.error = error
        super(FailedLookup, self).__init__("Failed lookup", *args, **kwargs)


class FailedVariableLookup(Exception):
    """Lookup could not be resolved.

    Raised when an exception is raised when trying to resolve a lookup.

    """

    def __init__(self, variable_name, lookup, error, *args, **kwargs):
        """Instantiate class.

        Args:
            variable_name (str): Name of the variable that failed to be
                resolved.
            lookup (:class:`runway.cfngin.variables.VariableValueLookup`):
                Attempted lookup and resulted in an exception being raised.
            error (Exception): The exception that was raised.

        """
        self.lookup = lookup
        self.error = error
        message = "Couldn't resolve lookup in variable `%s`, " % variable_name
        message += "lookup: ${%s}: " % repr(lookup)
        message += "(%s) %s" % (error.__class__, error)
        super(FailedVariableLookup, self).__init__(message, *args, **kwargs)


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
        super(GraphError, self).__init__(message)


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
        super(ImproperlyConfigured, self).__init__(message, *args, **kwargs)


class InvalidConfig(Exception):
    """Provided config file is invalid."""

    def __init__(self, errors):
        """Instantiate class.

        Args:
            errors (Union[str, List[Union[Exception, str]]]): Errors or error
                messages that are raised to identify that a config is invalid.

        """
        super(InvalidConfig, self).__init__(errors)
        self.errors = errors


class InvalidDockerizePipConfiguration(Exception):
    """Raised when the provided configuration for dockerized pip is invalid."""

    def __init__(self, msg):
        """Instantiate class.

        Args:
            msg (str): The reason for the error being raised.

        """
        self.message = msg
        super(InvalidDockerizePipConfiguration, self).__init__(self.message)


class InvalidLookupCombination(Exception):
    """Improper use of lookups to result in a non-string return value."""

    def __init__(self, lookup, lookups, value, *args, **kwargs):
        """Instantiate class.

        Args:
            lookup (:class:`runway.cfngin.variables.VariableValueLookup`): The
                variable lookup that was attempted but did not return a string.
            lookups (:class:`runway.cfngin.variables.VariableValueConcatenation`):
                The full variable concatenation the failing lookup is part of.
            value (Any): The non-string value returned by lookup.

        """
        message = (
            'Lookup: "{}" has non-string return value, must be only lookup '
            'present (not {}) in "{}"'
        ).format(str(lookup), len(lookups), value)
        super(InvalidLookupCombination, self).__init__(message, *args, **kwargs)


class InvalidLookupConcatenation(Exception):
    """Intermediary Exception to be converted to InvalidLookupCombination.

    Should be caught by error handling and
    :class:`runway.cfngin.exceptions.InvalidLookupCombination` raised instead
    to construct a propper error message.

    """

    def __init__(self, lookup, lookups, *args, **kwargs):
        """Instantiate class."""
        self.lookup = lookup
        self.lookups = lookups
        super(InvalidLookupConcatenation, self).__init__("", *args, **kwargs)


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
        super(InvalidUserdataPlaceholder, self).__init__(message, *args, **kwargs)


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
        super(MissingEnvironment, self).__init__(message, *args, **kwargs)


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
        super(MissingParameterException, self).__init__(message, *args, **kwargs)


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
        super(MissingVariable, self).__init__(message, *args, **kwargs)


class OutputDoesNotExist(Exception):
    """Raised when a specific stack output does not exist."""

    def __init__(self, stack_name, output, *args, **kwargs):
        """Instantiate class.

        Args:
            stack_name (str): Name of the stack.
            output (str): The output that does not exist.

        """
        self.stack_name = stack_name
        self.output = output

        message = "Output %s does not exist on stack %s" % (output, stack_name)
        super(OutputDoesNotExist, self).__init__(message, *args, **kwargs)


class PipError(Exception):
    """Raised when pip returns a non-zero exit code."""

    def __init__(self):
        """Instantiate class."""
        self.message = (
            "A non-zero exit code was returned when invoking "
            "pip. More information can be found in the error above."
        )
        super(PipError, self).__init__(self.message)


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
        super(PipenvError, self).__init__(self.message)


class PersistentGraphCannotLock(Exception):
    """Raised when the persistent graph in S3 cannot be locked."""

    def __init__(self, reason):
        """Instantiate class."""
        message = "Could not lock persistent graph; %s" % reason
        super(PersistentGraphCannotLock, self).__init__(message)


class PersistentGraphCannotUnlock(Exception):
    """Raised when the persistent graph in S3 cannot be unlocked."""

    def __init__(self, reason):
        """Instantiate class."""
        message = "Could not unlock persistent graph; %s" % reason
        super(PersistentGraphCannotUnlock, self).__init__(message)


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
        super(PersistentGraphLocked, self).__init__(message)


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
        super(PersistentGraphLockCodeMissmatch, self).__init__(message)


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
        super(PersistentGraphUnlocked, self).__init__(message)


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

        super(PlanFailed, self).__init__(message, *args, **kwargs)


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
        super(StackDoesNotExist, self).__init__(message, *args, **kwargs)


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
        super(StackUpdateBadStatus, self).__init__(message, *args, **kwargs)


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
        super(StackFailed, self).__init__(message)


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

        super(UnableToExecuteChangeSet, self).__init__(message)


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

        super(UnhandledChangeSetStatus, self).__init__(message)


class UnknownLookupType(Exception):
    """Lookup type provided does not match a registered lookup.

    Example:
        If a lookup of ``${<lookup_type> query}`` is used and ``<lookup_type>``
        is not a registered lookup, this exception will be raised.

    """

    def __init__(self, lookup_type, *args, **kwargs):
        """Instantiate class.

        Args:
            lookup_type (str): Lookup type that was used but not registered.

        """
        message = 'Unknown lookup type: "{}"'.format(lookup_type)
        super(UnknownLookupType, self).__init__(message, *args, **kwargs)


class UnresolvedVariable(Exception):
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
        super(UnresolvedVariable, self).__init__(message, *args, **kwargs)


class UnresolvedVariableValue(Exception):
    """Intermediary Exception to be converted to UnresolvedVariable.

    Should be caught by error handling and
    :class:`runway.cfngin.exceptions.UnresolvedVariable` raised instead to
    construct a propper error message.

    """

    def __init__(self, lookup, *args, **kwargs):
        """Instantiate class.

        Args:
            lookup (:class:`runway.cfngin.variables.VariableValueLookup`): The
                lookup that is not resolved.

        """
        self.lookup = lookup
        super(UnresolvedVariableValue, self).__init__(
            "Unresolved lookup", *args, **kwargs
        )


class UnresolvedVariables(Exception):
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
        super(UnresolvedVariables, self).__init__(message, *args, **kwargs)


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
        super(ValidatorError, self).__init__()

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
        super(VariableTypeRequired, self).__init__(message, *args, **kwargs)
