"""CFNgin stack."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from runway.utils import load_object_from_string
from runway.variables import Variable, resolve_variables

from .blueprints.raw import RawTemplateBlueprint

if TYPE_CHECKING:
    from typing_extensions import Literal

    from ..config.models.cfngin import CfnginStackDefinitionModel
    from ..context import CfnginContext
    from .blueprints.base import Blueprint
    from .providers.aws.default import Provider


def _initialize_variables(
    stack_def: CfnginStackDefinitionModel, variables: dict[str, Any] | None = None
) -> list[Variable]:
    """Convert defined variables into a list of ``Variable`` for consumption.

    Args:
        stack_def: The stack definition being worked on.
        variables: Optional, explicit variables.

    Returns:
        Contains key/value pairs of the collected variables.

    Raises:
        AttributeError: Raised when the stack definition contains an invalid
            attribute. Currently only when using old parameters, rather than
            variables.

    """
    variables = variables or stack_def.variables or {}
    variable_values = deepcopy(variables)
    return [Variable(k, v, "cfngin") for k, v in variable_values.items()]


class Stack:
    """Represents gathered information about a stack to be built/updated.

    Attributes:
        definition: The stack definition from the config.
        enabled: Whether this stack is enabled
        force: Whether to force updates on this stack.
        fqn: Fully qualified name of the stack. Combines the stack name
            and current namespace.
        in_progress_behavior: The behavior for when a stack is in
            ``CREATE_IN_PROGRESS`` or ``UPDATE_IN_PROGRESS``.
        locked: Whether or not the stack is locked.
        logging: Whether logging is enabled.
        mappings: Cloudformation mappings passed to the blueprint.
        name: Name of the stack taken from the definition.
        outputs: CloudFormation Stack outputs.
        protected: Whether this stack is protected.
        termination_protection: The state of termination protection
            to apply to the stack.
        variables: Variables for the stack.

    """

    _blueprint: Blueprint | None
    _stack_policy: str | None

    context: CfnginContext
    definition: CfnginStackDefinitionModel
    enabled: bool
    force: bool
    fqn: str
    in_progress_behavior: Literal["wait"] | None
    locked: bool
    logging: bool
    mappings: dict[str, dict[str, dict[str, Any]]]
    name: str
    outputs: dict[str, Any]
    protected: bool
    termination_protection: bool
    variables: list[Variable]

    def __init__(
        self,
        definition: CfnginStackDefinitionModel,
        context: CfnginContext,
        *,
        variables: dict[str, Any] | None = None,
        mappings: dict[str, dict[str, dict[str, Any]]] | None = None,
        locked: bool = False,
        force: bool = False,
        enabled: bool = True,
        protected: bool = False,
    ) -> None:
        """Instantiate class.

        Args:
            definition: A stack definition.
            context: Current context for deploying the stack.
            variables: Variables for the stack.
            mappings: Cloudformation mappings passed to the blueprint.
            locked: Whether or not the stack is locked.
            force: Whether to force updates on this stack.
            enabled: Whether this stack is enabled
            protected: Whether this stack is protected.

        """
        self._blueprint = None
        self._stack_policy = None

        self.name = definition.name  # dependency of other attrs
        self.context = context
        self.definition = definition
        self.enabled = enabled
        self.force = force
        self.fqn = context.get_fqn(definition.stack_name or self.name)
        self.in_progress_behavior = definition.in_progress_behavior
        self.locked = locked
        self.logging = True
        self.mappings = mappings or {}
        self.outputs = {}
        self.protected = protected
        self.termination_protection = definition.termination_protection
        self.variables = _initialize_variables(definition, variables)

    @property
    def required_by(self) -> set[str]:
        """Return a list of stack names that depend on this stack."""
        return set(self.definition.required_by)

    @property
    def requires(self) -> set[str]:
        """Return a list of stack names this stack depends on."""
        requires = set(self.definition.requires or [])

        # Add any dependencies based on output lookups
        for variable in self.variables:
            deps = variable.dependencies
            if self.name in deps:
                raise ValueError(
                    f"Variable {variable.name} in stack {self.name} has a circular reference"
                )
            requires.update(deps)
        return requires

    @property
    def stack_policy(self) -> str | None:
        """Return the Stack Policy to use for this stack."""
        if self.definition.stack_policy_path:
            return self.definition.stack_policy_path.read_text() or None
        return None

    @property
    def blueprint(self) -> Blueprint:
        """Return the blueprint associated with this stack."""
        if not self._blueprint:
            kwargs: dict[str, Any] = {}
            if self.definition.class_path:
                class_path = self.definition.class_path
                blueprint_class = load_object_from_string(class_path)
                if not hasattr(blueprint_class, "rendered"):
                    raise AttributeError(
                        f'Stack class {class_path} does not have a "rendered" attribute.'
                    )
            elif self.definition.template_path:
                blueprint_class = RawTemplateBlueprint
                kwargs["raw_template_path"] = self.definition.template_path
            else:
                raise AttributeError("Stack does not have a defined class or template path.")

            self._blueprint = cast(
                "Blueprint",
                blueprint_class(
                    name=self.name,
                    context=self.context,
                    mappings=self.mappings,
                    description=self.definition.description,
                    **kwargs,
                ),
            )
        return self._blueprint

    @property
    def tags(self) -> dict[str, Any]:
        """Return the tags that should be set on this stack.

        Includes both the global tags, as well as any stack specific tags
        or overrides.

        """
        tags = self.definition.tags or {}
        return dict(self.context.tags, **tags)

    @property
    def parameter_values(self) -> dict[str, Any]:
        """Return all CloudFormation Parameters for the stack.

        CloudFormation Parameters can be specified via Blueprint Variables
        with a :class:`runway.cfngin.blueprints.variables.types.CFNType`
        ``type``.

        Returns:
            Dictionary of ``<parameter name>: <parameter value>``.

        """
        return self.blueprint.parameter_values

    @property
    def all_parameter_definitions(self) -> dict[str, Any]:
        """Return all parameters in the blueprint/template."""
        return self.blueprint.parameter_definitions

    @property
    def required_parameter_definitions(self) -> dict[str, Any]:
        """Return all CloudFormation Parameters without a default value."""
        return self.blueprint.required_parameter_definitions

    def resolve(self, context: CfnginContext, provider: Provider | None = None) -> None:
        """Resolve the Stack variables.

        This resolves the Stack variables and then prepares the Blueprint for
        rendering by passing the resolved variables to the Blueprint.

        Args:
            context: CFNgin context.
            provider: Subclass of the base provider.

        """
        resolve_variables(self.variables, context, provider)
        self.blueprint.resolve_variables(self.variables)

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        """Set stack outputs to the provided value.

        Args:
            outputs: CloudFormation Stack outputs.

        """
        self.outputs = outputs

    def __repr__(self) -> str:
        """Object represented as a string."""
        return self.fqn
