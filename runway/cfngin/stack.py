"""CFNgin stack."""
from copy import deepcopy

from runway.util import load_object_from_string
from runway.variables import Variable, resolve_variables

from .blueprints.raw import RawTemplateBlueprint


def _initialize_variables(stack_def, variables=None):
    """Convert defined variables into a list of ``Variable`` for consumption.

    Args:
        stack_def (Dict[str, Any]): The stack definition being worked on.
        variables (Dict[str, Any]): Optional, explicit variables.

    Returns:
        List[Variable]: Contains key/value pairs of the collected variables.

    Raises:
        AttributeError: Raised when the stack definition contains an invalid
            attribute. Currently only when using old parameters, rather than
            variables.

    """
    variables = variables or stack_def.variables or {}
    variable_values = deepcopy(variables)
    return [Variable(k, v, 'cfngin') for k, v in variable_values.items()]


class Stack(object):
    """Represents gathered information about a stack to be built/updated.

    Attributes:
        definition (:class:`runway.cfngin.config.Stack`): The stack definition
            from the config.
        enabled (bool): Whether this stack is enabled
        force (bool): Whether to force updates on this stack.
        fqn (str): Fully qualified name of the stack. Combines the stack name
            and current namespace.
        in_progress_behavior (Optional[str]): The behavior for when a stack is
            in ``CREATE_IN_PROGRESS`` or ``UPDATE_IN_PROGRESS``.
        locked (bool): Whether or not the stack is locked.
        logging (bool): Whether logging is enabled.
        mappings (Optional[Dict[str, Dict[str, Any]]]): Cloudformation
            mappings passed to the blueprint.
        name (str): Name of the stack taken from the definition.
        outputs (Optional[Dict[str, Any]]): CloudFormation Stack outputs
        profile (str): Profile name from the stack definition.
        protected (bool): Whether this stack is protected.
        region (str): AWS region name.
        termination_protection (bool): The state of termination protection
            to apply to the stack.
        variables (Optional[Dict[str, Any]]): Variables for the stack.

    """

    def __init__(self, definition, context, variables=None, mappings=None,
                 locked=False, force=False, enabled=True, protected=False):
        """Instantiate class.

        Args:
            definition (:class:`runway.cfngin.config.Stack`): A stack
                definition.
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack.
            variables (Optional[Dict[str, Any]]): Variables for the stack.
            mappings (Optional[Dict[str, Dict[str, Any]]]): Cloudformation
                mappings passed to the blueprint.
            locked (bool): Whether or not the stack is locked.
            force (bool): Whether to force updates on this stack.
            enabled (bool): Whether this stack is enabled
            protected (bool): Whether this stack is protected.

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
        self.mappings = mappings
        self.outputs = None
        self.profile = definition.profile
        self.protected = protected
        self.region = definition.region
        self.termination_protection = definition.termination_protection
        self.variables = _initialize_variables(definition, variables)

    @property
    def required_by(self):
        """Return a list of stack names that depend on this stack.

        Returns:
            List[str]

        """
        return self.definition.required_by or []

    @property
    def requires(self):
        """Return a list of stack names this stack depends on.

        Returns:
            List[str]

        """
        requires = set(self.definition.requires or [])

        # Add any dependencies based on output lookups
        for variable in self.variables:
            deps = variable.dependencies
            if self.name in deps:
                message = (
                    "Variable %s in stack %s has a circular reference"
                ) % (variable.name, self.name)
                raise ValueError(message)
            requires.update(deps)
        return requires

    @property
    def stack_policy(self):
        """Return the Stack Policy to use for this stack."""
        if not self._stack_policy:
            self._stack_policy = None
            if self.definition.stack_policy_path:
                with open(self.definition.stack_policy_path) as file_:
                    self._stack_policy = file_.read()

        return self._stack_policy

    @property
    def blueprint(self):
        """Return the blueprint associated with this stack."""
        if not self._blueprint:
            kwargs = {}
            blueprint_class = None
            if self.definition.class_path:
                class_path = self.definition.class_path
                blueprint_class = load_object_from_string(class_path)
                if not hasattr(blueprint_class, "rendered"):
                    raise AttributeError("Stack class %s does not have a "
                                         "\"rendered\" "
                                         "attribute." % (class_path,))
            elif self.definition.template_path:
                blueprint_class = RawTemplateBlueprint
                kwargs["raw_template_path"] = self.definition.template_path
            else:
                raise AttributeError("Stack does not have a defined class or "
                                     "template path.")

            self._blueprint = blueprint_class(
                name=self.name,
                context=self.context,
                mappings=self.mappings,
                description=self.definition.description,
                **kwargs
            )
        return self._blueprint

    @property
    def tags(self):
        """Return the tags that should be set on this stack.

        Includes both the global tags, as well as any stack specific tags
        or overrides.

        Returns:
            Dict[str, str]: Dictionary of tags.

        """
        tags = self.definition.tags or {}
        return dict(self.context.tags, **tags)

    @property
    def parameter_values(self):
        """Return all CloudFormation Parameters for the stack.

        CloudFormation Parameters can be specified via Blueprint Variables
        with a :class:`runway.cfngin.blueprints.variables.types.CFNType`
        ``type``.

        Returns:
            Dict[str, Any]: dictionary of
            ``<parameter name>: <parameter value>``.

        """
        return self.blueprint.get_parameter_values()

    @property
    def all_parameter_definitions(self):
        """Return a list of all parameters in the blueprint/template.

        Dict[str, Dict[str, str]]: parameter definitions. Keys are
        parameter names, the values are dicts containing key/values
        for various parameter properties.

        """
        return self.blueprint.get_parameter_definitions()

    @property
    def required_parameter_definitions(self):
        """Return all CloudFormation Parameters without a default value.

        Returns:
            Dict[str, Dict[str, str]]: dict of required CloudFormation
            Parameters for the blueprint. Will be a dictionary of
            ``<parameter name>: <parameter attributes>``.

        """
        return self.blueprint.get_required_parameter_definitions()

    def resolve(self, context, provider):
        """Resolve the Stack variables.

        This resolves the Stack variables and then prepares the Blueprint for
        rendering by passing the resolved variables to the Blueprint.

        Args:
            context (:class:`runway.cfngin.context.Context`): CFNgin context.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Subclass of the base provider.

        """
        resolve_variables(self.variables, context, provider)
        self.blueprint.resolve_variables(self.variables)

    def set_outputs(self, outputs):
        """Set stack outputs to the provided value.

        Args:
            outputs (Dict[str, Any]): CloudFormation Stack outputs.

        """
        self.outputs = outputs

    def __repr__(self):
        """Object represented as a string."""
        return self.fqn
