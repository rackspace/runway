"""Runway exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .utils import DOC_SITE

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from .variables import (
        Variable,
        VariableValue,
        VariableValueConcatenation,
        VariableValueLookup,
    )


class RunwayError(Exception):
    """Base class for custom exceptions raised by Runway."""

    message: str
    """Error message."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class."""
        if self.message:
            super().__init__(self.message, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


class ConfigNotFound(RunwayError):
    """Configuration file could not be found."""

    looking_for: list[str]
    message: str
    path: Path

    def __init__(self, *, looking_for: list[str] | None = None, path: Path) -> None:
        """Instantiate class.

        Args:
            path: Path where the config file was expected to be found.
            looking_for: List of file names that were being looked for.

        """
        self.looking_for = looking_for or []
        self.path = path

        if looking_for:
            self.message = f"config file not found at path {path}; looking for one of {looking_for}"
        else:
            self.message = f"config file not found at path {path}"
        super().__init__(self.path, self.looking_for)


class DockerConnectionRefusedError(RunwayError):
    """Docker connection refused.

    This can be caused by a number of reasons:

    - Docker is not installed.
    - Docker service is not running.
    - The current user does not have adequate permissions (e.g. not a member of
      the ``docker`` group).

    """

    def __init__(self) -> None:
        """Instantiate class."""
        self.message = (
            "Docker connection refused; install Docker, ensure it is running, "
            "and ensure the current user has adequate permissions"
        )
        super().__init__()


class DockerExecFailedError(RunwayError):
    """Docker failed when trying to execute a command.

    This can be used for ``docker container run``, ``docker container start``
    and ``docker exec`` equivalents.

    """

    exit_code: int
    """The ``StatusCode`` returned by Docker."""

    def __init__(self, response: dict[str, Any]) -> None:
        """Instantiate class.

        Args:
            response: The return value of :meth:`docker.models.containers.Container.wait`,
                Docker API's response as a Python dictionary.
                This can contain important log information pertinent to troubleshooting
                that may not streamed.

        """
        self.exit_code = response.get("StatusCode", 1)  # we can assume this will be > 0
        error: dict[Any, Any] = response.get("Error") or {}  # value from dict could be NoneType
        self.message = error.get("Message", "error message undefined")
        super().__init__()


class FailedLookup(RunwayError):
    """Intermediary Exception to be converted to FailedVariableLookup.

    Should be caught by error handling and
    :class:`runway.cfngin.exceptions.FailedVariableLookup` raised instead to
    construct a proper error message.

    """

    cause: Exception
    lookup: VariableValueLookup
    message: str = "Failed lookup"

    def __init__(
        self, lookup: VariableValueLookup, cause: Exception, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            lookup: The variable value lookup that was attempted and
                resulted in an exception being raised.
            cause: The exception that was raised.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.cause = cause
        self.lookup = lookup
        super().__init__(*args, **kwargs)


class FailedVariableLookup(RunwayError):
    """Lookup could not be resolved.

    Raised when an exception is raised when trying to resolve a lookup.

    """

    cause: FailedLookup
    variable: Variable
    message: str

    def __init__(
        self, variable: Variable, lookup_error: FailedLookup, *args: Any, **kwargs: Any
    ) -> None:
        """Instantiate class.

        Args:
            variable: The variable containing the failed lookup.
            lookup_error: The exception that was raised directly before this one.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.cause = lookup_error
        self.variable = variable
        self.message = (
            f'Could not resolve lookup "{lookup_error.lookup}" for variable "{variable.name}"'
        )
        super().__init__(*args, **kwargs)


class HclParserError(RunwayError):
    """HCL/HCL2 parser error."""

    message: str

    def __init__(
        self,
        exc: Exception,
        file_path: Path | str,
        parser: ModuleType | None = None,
    ) -> None:
        """Instantiate class.

        Args:
            exc: Exception that was raised.
            file_path: File that resulted in the error.
            parser: The parser what was used to try to parse the file (hcl|hcl2).

        """
        self.reason = exc
        self.file_path = file_path
        if parser:
            self.message = f"Unable to parse {file_path} as {parser.__name__.upper()}\n\n{exc}"
        else:
            self.message = f"Unable to parse {file_path}\n\n{exc}"
        super().__init__()


class InvalidLookupConcatenation(RunwayError):
    """Invalid return value for a concatenated (chained) lookup.

    The return value must be a string when lookups are concatenated.

    """

    concatenated_lookups: VariableValueConcatenation[Any]
    invalid_lookup: VariableValue
    message: str

    def __init__(
        self,
        invalid_lookup: VariableValue,
        concat_lookups: VariableValueConcatenation[Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Instantiate class."""
        self.concatenated_lookups = concat_lookups
        self.invalid_lookup = invalid_lookup
        self.message = (
            f"expected return value of type {str} but received "
            f'{type(invalid_lookup.value)} for lookup "{invalid_lookup}" '
            f'in "{concat_lookups}"'
        )
        super().__init__(*args, **kwargs)


class KubectlVersionNotSpecified(RunwayError):
    """kubectl version is required but was not specified.

    Version can be specified by using a file or option.

    """

    message: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class."""
        self.message = (
            "kubectl version not specified. Learn how to use Runway to manage kubectl versions "
            f"at {DOC_SITE}/page/kubernetes/advanced_features.html#version-management"
        )
        super().__init__(*args, **kwargs)


class NpmNotFound(RunwayError):
    """Raised when npm could not be executed or was not found in path."""

    message: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Instantiate class."""
        self.message = (
            '"npm" not found in path or is not executable; '
            "please ensure it is installed correctly"
        )
        super().__init__(*args, **kwargs)


class OutputDoesNotExist(RunwayError):
    """Raised when a specific stack output does not exist."""

    output: str
    """Name of the CloudFormation Stack's Output that does not exist."""

    stack_name: str
    """Name of a CloudFormation Stack."""

    def __init__(self, stack_name: str, output: str, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            stack_name: Name of the stack.
            output: The output that does not exist.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.stack_name = stack_name
        self.output = output

        self.message = f"Output {output} does not exist on stack {stack_name}"
        super().__init__(*args, **kwargs)


class RequiredTagNotFoundError(RunwayError):
    """Required tag not found on resource."""

    resource: str
    """An ID or name to identify a resource."""

    tag_key: str
    """Key of the tag that could not be found."""

    def __init__(self, resource: str, tag_key: str) -> None:
        """Instantiate class.

        Args:
            resource: An ID or name to identify a resource.
            tag_key: Key of the tag that could not be found.

        """
        self.resource = resource
        self.tag_key = tag_key
        self.message = f"required tag '{tag_key}' not found for {resource}"
        super().__init__()


class UnknownLookupType(RunwayError):
    """Lookup type provided does not match a registered lookup.

    Example:
        If a lookup of ``${<lookup_type> query}`` is used and ``<lookup_type>``
        is not a registered lookup, this exception will be raised.

    """

    message: str

    def __init__(self, lookup: VariableValueLookup, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            lookup: Variable value lookup that could not find a handler.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.message = f'Unknown lookup type "{lookup.lookup_name.value}" in "{lookup}"'
        super().__init__(*args, **kwargs)


class UnresolvedVariable(RunwayError):
    """Raised when trying to use a variable before it has been resolved."""

    message: str

    def __init__(self, variable: Variable, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            variable: The unresolved variable.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.message = f'Attempted to use variable "{variable.name}" before it was resolved'
        self.variable = variable
        super().__init__(*args, **kwargs)


class UnresolvedVariableValue(RunwayError):
    """Intermediary Exception to be converted to UnresolvedVariable.

    Should be caught by error handling and
    :class:`runway.cfngin.exceptions.UnresolvedVariable` raised instead to
    construct a proper error message.

    """

    lookup: VariableValueLookup
    message: str = "Unresolved lookup"

    def __init__(self, lookup: VariableValueLookup, *args: Any, **kwargs: Any) -> None:
        """Instantiate class.

        Args:
            lookup: The variable value lookup that is not resolved.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        """
        self.lookup = lookup
        super().__init__(*args, **kwargs)


class VariablesFileNotFound(RunwayError):
    """Defined variables file could not be found."""

    file_path: Path
    message: str

    def __init__(self, file_path: Path) -> None:
        """Instantiate class.

        Args:
            file_path: Path where the file was expected to be found.

        """
        self.file_path = file_path
        self.message = f"defined variables file not found at path {file_path}"
        super().__init__(self.file_path)
