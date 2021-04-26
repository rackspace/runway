"""CFNgin Blueprint type definitions."""
from __future__ import annotations

from typing import Any, Callable, List

from typing_extensions import TypedDict


class _RequiredBlueprintVariableTypeDef(TypedDict, total=False):
    """Type definition for runway.cfngin.blueprints.base.Blueprint.VARIABLES items."""

    type: Any


class _OptionalBlueprintVariableTypeDef(TypedDict, total=False):
    """Type definition for runway.cfngin.blueprints.base.Blueprint.VARIABLES items."""

    allowed_pattern: str
    allowed_values: List[Any]
    constraint_description: str
    default: Any
    description: str
    max_length: int
    max_value: int
    min_length: int
    min_value: int
    no_echo: bool
    validator: Callable[[Any], Any]


class BlueprintVariableTypeDef(
    _RequiredBlueprintVariableTypeDef, _OptionalBlueprintVariableTypeDef
):
    """Type definition for :attr:`runway.cfngin.blueprints.base.Blueprint.VARIABLES` items.

    Attributes:
        allowed_pattern: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            A regular expression that represents the patterns you want to allow
            for the Cloudformation Parameter.
        allowed_values: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            The values that should be allowed for the CloudFormation Parameter.
        constraint_description: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            A string that explains the constraint when the constraint
            is violated for the CloudFormation Parameter.
        default: The default value that should be used for the variable if none is
                provided in the config.
        description: A string that describes the purpose of the variable.
        max_length: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            The maximum length of the value for the CloudFormation Parameter.
        max_value: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            The max value for the CloudFormation Parameter.
        min_length: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            The minimum length of the value for the CloudFormation Parameter.
        min_value: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            The minimum value for the CloudFormation Parameter.
        no_echo: Only valid for variables whose type subclasses
            :class:`~runway.cfngin.blueprints.variables.types.CFNType`.
            Whether to mask the parameter value whenever anyone makes a call that
            describes the stack. If you set the value to true, the parameter
            value is masked with asterisks (*****).
        type: The type for the variable value. This can either be a native python
            type or one of the CFNgin variable types.
        validator: An optional function that can do custom validation of the variable.
            A validator function should take a single argument, the value being
            validated, and should return the value if validation is successful.
            If there is an issue validating the value, an exception
            (``ValueError``, ``TypeError``, etc) should be raised by the function.

    """  # noqa
