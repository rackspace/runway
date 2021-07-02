"""CFNgin blueprint base classes."""
from __future__ import annotations

import copy
import hashlib
import logging
import string
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from troposphere import Output, Parameter, Ref, Template

from ...compat import cached_property
from ...variables import Variable
from ..exceptions import (
    InvalidUserdataPlaceholder,
    MissingVariable,
    UnresolvedBlueprintVariable,
    UnresolvedBlueprintVariables,
    ValidatorError,
    VariableTypeRequired,
)
from ..utils import read_value_from_path
from .variables.types import CFNType, TroposphereType

if TYPE_CHECKING:
    from ...context import CfnginContext
    from .type_defs import BlueprintVariableTypeDef

LOGGER = logging.getLogger(__name__)

PARAMETER_PROPERTIES = {
    "default": "Default",
    "description": "Description",
    "no_echo": "NoEcho",
    "allowed_values": "AllowedValues",
    "allowed_pattern": "AllowedPattern",
    "max_length": "MaxLength",
    "min_length": "MinLength",
    "max_value": "MaxValue",
    "min_value": "MinValue",
    "constraint_description": "ConstraintDescription",
}

_T = TypeVar("_T")


class CFNParameter:
    """Wrapper around a value to indicate a CloudFormation Parameter."""

    def __init__(self, name: str, value: Union[bool, int, List[Any], str, Any]) -> None:
        """Instantiate class.

        Args:
            name: The name of the CloudFormation Parameter.
            value: The value we're going to submit as a CloudFormation Parameter.

        """
        self.name = name
        if isinstance(value, (list, str)):
            self.value = value
        elif isinstance(value, bool):
            LOGGER.debug("converting parameter %s boolean '%s' to string", name, value)
            self.value = str(value).lower()
        elif isinstance(value, int):
            LOGGER.debug("converting parameter %s integer '%s' to string", name, value)
            self.value = str(value)
        else:
            raise TypeError(
                f"CFNParameter ({name}) value must be one of bool, int, str, "
                f"List[str] but got: {type(value)}"
            )

    def __repr__(self) -> str:
        """Object represented as a string."""
        return f"CFNParameter[{self.name}: {self.value}]"

    @cached_property
    def ref(self) -> Ref:
        """Ref the value of a parameter."""
        return Ref(self.name)

    def to_parameter_value(self) -> Union[List[Any], str]:
        """Return the value to be submitted to CloudFormation."""
        return self.value


def build_parameter(name: str, properties: BlueprintVariableTypeDef) -> Parameter:
    """Build a troposphere Parameter with the given properties.

    Args:
        name: The name of the parameter.
        properties: Contains the properties that will be applied to the parameter.
            See: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html

    Returns:
        The created parameter object.

    """  # noqa: E501
    param = Parameter(name, Type=properties.get("type"))
    for name_, attr in PARAMETER_PROPERTIES.items():
        if name_ in properties:
            setattr(param, attr, properties[name_])  # type: ignore
    return param


def validate_variable_type(
    var_name: str,
    var_type: Union[Type[CFNType], TroposphereType[Any], type],
    value: Any,
) -> Any:
    """Ensure the value is the correct variable type.

    Args:
        var_name: The name of the defined variable on a blueprint.
        var_type: The type that the value should be.
        value: The object representing the value provided for the variable

    Returns:
        The appropriate value object. If the original value was of CFNType, the
        returned value will be wrapped in CFNParameter.

    Raises:
        ValueError: If the `value` isn't of `var_type` and can't be cast as
            that type, this is raised.

    """
    if isinstance(var_type, TroposphereType):
        try:
            value = var_type.create(value)
        except Exception as exc:
            raise ValidatorError(
                var_name, f"{var_type.resource_name}.create", value, exc
            ) from exc
    elif issubclass(var_type, CFNType):
        value = CFNParameter(name=var_name, value=value)
    else:
        if not isinstance(value, var_type):
            raise TypeError(
                f"Value for variable {var_name} must be of type {var_type}. Actual "
                f"type: {type(value)}"
            )
    return value


def validate_allowed_values(allowed_values: Optional[List[Any]], value: Any) -> bool:
    """Support a variable defining which values it allows.

    Args:
        allowed_values: A list of allowed values from the variable definition.
        value: The object representing the value provided for the variable.

    Returns:
        Boolean for whether or not the value is valid.

    """
    # ignore CFNParameter, troposphere handles these for us
    if not allowed_values or isinstance(value, CFNParameter):
        return True
    return value in allowed_values


def resolve_variable(
    var_name: str,
    var_def: BlueprintVariableTypeDef,
    provided_variable: Optional[Variable],
    blueprint_name: str,
) -> Any:
    """Resolve a provided variable value against the variable definition.

    Args:
        var_name: The name of the defined variable on a blueprint.
        var_def: A dictionary representing the defined variables attributes.
        provided_variable: The variable value provided to the blueprint.
        blueprint_name: The name of the blueprint that the variable is being applied to.

    Returns:
        The resolved variable value, could be any python object.

    Raises:
        MissingVariable: Raised when a variable with no default is not
            provided a value.
        UnresolvedBlueprintVariable: Raised when the provided variable is
            not already resolved.
        ValueError: Raised when the value is not the right type and cannot be
            cast as the correct type. Raised by
            :func:`runway.cfngin.blueprints.base.validate_variable_type`
        ValidatorError: Raised when a validator raises an exception. Wraps the
            original exception.

    """
    try:
        var_type = var_def["type"]
    except KeyError:
        raise VariableTypeRequired(blueprint_name, var_name) from None

    if provided_variable:
        if not provided_variable.resolved:
            raise UnresolvedBlueprintVariable(blueprint_name, provided_variable)

        value = provided_variable.value
    else:
        # Variable value not provided, try using the default, if it exists
        # in the definition
        try:
            value = var_def["default"]
        except KeyError:
            raise MissingVariable(blueprint_name, var_name) from None

    # If no validator, return the value as is, otherwise apply validator
    validator = var_def.get("validator", lambda v: v)
    try:
        value = validator(value)
    except Exception as exc:
        raise ValidatorError(var_name, validator.__name__, value, exc) from exc

    # Ensure that the resulting value is the correct type
    value = validate_variable_type(var_name, var_type, value)

    allowed_values = var_def.get("allowed_values")
    if not validate_allowed_values(allowed_values, value):
        raise ValueError(
            f"Invalid value passed to {var_name} in Blueprint {blueprint_name}. "
            f"Got '{value}', expected one of {allowed_values}."
        )

    return value


def parse_user_data(
    variables: Dict[str, Any], raw_user_data: str, blueprint_name: str
) -> str:
    """Parse the given user data and renders it as a template.

    It supports referencing template variables to create userdata
    that's supplemented with information from the stack, as commonly
    required when creating EC2 userdata files.

    Example:
        Given a raw_user_data string: ``'open file ${file}'``
        And a variables dictionary with: ``{'file': 'test.txt'}``
        parse_user_data would output: ``open file test.txt``

    Args:
        variables: Variables available to the template.
        raw_user_data: The user_data to be parsed.
        blueprint_name: The name of the blueprint.

    Returns:
        The parsed user data, with all the variables values and refs replaced
        with their resolved values.

    Raises:
        InvalidUserdataPlaceholder: Raised when a placeholder name in
            raw_user_data is not valid. E.g ``${100}`` would raise this.
        MissingVariable: Raised when a variable is in the raw_user_data that
            is not given in the blueprint

    """
    variable_values: Dict[str, Any] = {}

    for key, value in variables.items():
        if isinstance(value, CFNParameter):
            variable_values[key] = value.to_parameter_value()
        else:
            variable_values[key] = value

    template = string.Template(raw_user_data)

    res = ""

    try:
        res = template.substitute(variable_values)
    except ValueError as exc:
        raise InvalidUserdataPlaceholder(blueprint_name, exc.args[0]) from exc
    except KeyError as exc:
        raise MissingVariable(blueprint_name, str(exc)) from exc

    return res


class Blueprint:
    """Base implementation for rendering a troposphere template.

    Attributes:
        VARIABLES: Class variable that defines the values that can be passed
            from CFNgin to the template. These definition include metadata used
            to validate the provided value and to propegate the variable to the
            resulting CloudFormation template.
        context: CFNgin context object.
        description: The description of the CloudFormation template that will
            be generated by this Blueprint.
        mappings: CloudFormation Mappings to be added to the template during the
            rendering process.
        name: Name of the Stack that will be created by the Blueprint.
        template: Troposphere template.

    """

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {}

    context: CfnginContext
    description: Optional[str]
    mappings: Optional[Dict[str, Dict[str, Any]]]
    name: str
    template: Template

    def __init__(
        self,
        name: str,
        context: CfnginContext,
        *,
        description: Optional[str] = None,
        mappings: Optional[Dict[str, Dict[str, Any]]] = None,
        template: Optional[Template] = None,
        **_: Any,
    ):
        """Instantiate class.

        Args:
            name: A name for the blueprint.
            context: Context the blueprint is being executed under.
            description: The description of the CloudFormation template that will
                be generated by this blueprint.
            mappings: CloudFormation Mappings to be used in the template during
                the rendering process.
            template: Optionally, provide a preexisting Template.

        .. versionchanged:: 2.0.0
            Added :attr:`template`.

        .. versionchanged:: 2.0.0
            Class only takes 2 positional arguments.
            The rest are now keyword arguments.

        """
        self._rendered = None
        self._resolved_variables: Optional[Dict[str, Any]] = None
        self._version = None
        self.context = context
        self.description = description
        self.mappings = mappings
        self.name = name
        self.template = template or Template()

        if hasattr(self, "PARAMETERS") or hasattr(self, "LOCAL_PARAMETERS"):
            raise AttributeError(
                f"DEPRECATION WARNING: Blueprint {name} uses "
                "deprecated PARAMETERS or "
                "LOCAL_PARAMETERS, rather than VARIABLES. "
                "Please update your blueprints. See "
                "https://docs.onica.com/projects/runway/page/cfngin/blueprints.html#variables "
                "for additional information."
            )

    @cached_property
    def cfn_parameters(self) -> Dict[str, Union[List[Any], str]]:
        """Return a dict of variables with type :class:`~runway.cfngin.blueprints.variables.types.CFNType`.

        .. versionadded:: 2.0.0

        Returns:
            Variables that need to be submitted as CloudFormation Parameters.

        """  # noqa
        output: Dict[str, Union[List[Any], str]] = {}
        for key, value in self.variables.items():
            if hasattr(value, "to_parameter_value"):
                output[key] = value.to_parameter_value()
        return output

    def create_template(self) -> None:
        """Abstract method called to create a template from the blueprint."""
        raise NotImplementedError

    @property
    def defined_variables(self) -> Dict[str, BlueprintVariableTypeDef]:
        """Return a copy of :attr:`VARIABLES` to avoid accidental modification of the ClassVar.

        .. versionchanged:: 2.0.0
            Changed from a method to a property.

        """
        return copy.deepcopy(self.VARIABLES)

    @property
    def output_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get the output definitions.

        .. versionadded:: 2.0.0

        Returns:
            Output definitions. Keys are output names, the values are dicts
            containing key/values for various output properties.

        """
        return {k: output.to_dict() for k, output in self.template.outputs.items()}

    @cached_property
    def parameter_definitions(self) -> Dict[str, BlueprintVariableTypeDef]:
        """Get the parameter definitions to submit to CloudFormation.

        Any variable definition whose type is an instance of
        :class:`~runway.cfngin.blueprints.variables.types.CFNType` will
        be returned as a CloudFormation Parameter.

        .. versionadded:: 2.0.0

        Returns:
            Parameter definitions. Keys are parameter names, the values are dicts
            containing key/values for various parameter properties.

        """
        output: Dict[str, BlueprintVariableTypeDef] = {}
        for var_name, attrs in self.defined_variables.items():
            var_type = attrs.get("type")
            if isinstance(var_type, type) and issubclass(var_type, CFNType):
                cfn_attrs = copy.deepcopy(attrs)
                cfn_attrs["type"] = var_type.parameter_type
                output[var_name] = cfn_attrs
        return output

    @cached_property
    def parameter_values(self) -> Dict[str, Union[List[Any], str]]:
        """Return a dict of variables with type :class:`~runway.cfngin.blueprints.variables.types.CFNType`.

        .. versionadded:: 2.0.0

        Returns:
            Variables that need to be submitted as CloudFormation Parameters.
            Will be a dictionary of <parameter name>: <parameter value>.

        """  # noqa
        output: Dict[str, Any] = {}
        for key, value in self.variables.items():
            try:
                output[key] = value.to_parameter_value()
            except AttributeError:
                continue
        return output

    @property
    def rendered(self) -> str:
        """Return rendered blueprint."""
        if not self._rendered:
            self._version, self._rendered = self.render_template()
        return self._rendered

    @cached_property
    def required_parameter_definitions(self) -> Dict[str, BlueprintVariableTypeDef]:
        """Return all template parameters that do not have a default value.

        .. versionadded:: 2.0.0

        Returns:
            Dict of required CloudFormation Parameters for the blueprint.
            Will be a dictionary of ``<parameter name>: <parameter attributes>``.

        """
        return {
            name: attrs
            for name, attrs in self.parameter_definitions.items()
            if "Default" not in attrs
        }

    @property
    def requires_change_set(self) -> bool:
        """Return true if the underlying template has transforms."""
        return self.template.transform is not None

    @property
    def variables(self) -> Dict[str, Any]:
        """Return a Dict of variables available to the Template.

        These variables will have been defined within :attr:`VARIABLES` or
        :attr:`defined_variables`.
        Any variable value that contains a Lookup will have been resolved.

        .. versionadded:: 2.0.0

        Returns:
            Variables available to the Template.

        Raises:
            UnresolvedBlueprintVariables: If variables are unresolved.

        """
        if self._resolved_variables is None:
            raise UnresolvedBlueprintVariables(self.name)
        return self._resolved_variables

    @variables.setter
    def variables(self, value: Dict[str, Any]) -> None:
        """Setter for :meth:`variables`.

        .. versionadded:: 2.0.0

        """
        self._resolved_variables = value
        # clear cached properties that rely on this property
        try:
            del self.cfn_parameters
        except Exception:  # pylint: disable=broad-except
            pass
        try:
            del self.parameter_values
        except Exception:  # pylint: disable=broad-except
            pass

    @property
    def version(self) -> str:
        """Template version."""
        if not self._version:
            self._version, self._rendered = self.render_template()
        return self._version

    def add_output(self, name: str, value: Any) -> None:
        """Add an output to the template.

        Wrapper for ``self.template.add_output(Output(name, Value=value))``.

        Args:
            name: The name of the output to create.
            value: The value to put in the output.

        """
        self.template.add_output(Output(name, Value=value))

    def get_cfn_parameters(self) -> Dict[str, Union[List[Any], str]]:
        """Return a dictionary of variables with `type` :class:`CFNType`.

        .. deprecated:: 2.0.0
            Replaced by :attr:`cfn_parameters`.

        Returns:
            Variables that need to be submitted as CloudFormation Parameters.

        """
        LOGGER.warning(
            "%s.get_cfn_parameters is deprecated and will be removed in a future release",
            self.__class__.__name__,
        )
        return self.cfn_parameters

    def get_output_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get the output definitions.

        .. deprecated:: 2.0.0
            Replaced by :attr:`output_definitions`.

        Returns:
            Output definitions. Keys are output names, the values are dicts
            containing key/values for various output properties.

        """
        LOGGER.warning(
            "%s.get_output_definitions is deprecated and will be removed in a future release",
            self.__class__.__name__,
        )
        return self.output_definitions

    def get_parameter_definitions(self) -> Dict[str, BlueprintVariableTypeDef]:
        """Get the parameter definitions to submit to CloudFormation.

        Any variable definition whose `type` is an instance of
        :class:`~runway.cfngin.blueprints.variables.types.CFNType` will
        be returned as a CloudFormation Parameter.

        .. deprecated:: 2.0.0
            Replaced by :attr:`parameter_definitions`.

        Returns:
            Parameter definitions. Keys are parameter names, the values are dicts
            containing key/values for various parameter properties.

        """
        LOGGER.warning(
            "%s.get_parameter_definitions is deprecated and will be removed in a future release",
            self.__class__.__name__,
        )
        return self.parameter_definitions

    def get_parameter_values(self) -> Dict[str, Union[List[Any], str]]:
        """Return a dict of variables with type :class:`~runway.cfngin.blueprints.variables.types.CFNType`.

        .. deprecated:: 2.0.0
            Replaced by :attr:`parameter_values`.

        Returns:
            Variables that need to be submitted as CloudFormation Parameters.
            Will be a dictionary of <parameter name>: <parameter value>.

        """  # noqa
        LOGGER.warning(
            "%s.get_parameter_values is deprecated and will be removed in a future release",
            self.__class__.__name__,
        )
        return self.parameter_values

    def get_required_parameter_definitions(self) -> Dict[str, BlueprintVariableTypeDef]:
        """Return all template parameters that do not have a default value.

        .. deprecated:: 2.0.0
            Replaced by :attr:`required_parameter_definitions`.

        Returns:
            Dict of required CloudFormation Parameters for the blueprint.
            Will be a dictionary of ``<parameter name>: <parameter attributes>``.

        """
        LOGGER.warning(
            "%s.get_required_parameter_definitions is deprecated and will be removed "
            "in a future release",
            self.__class__.__name__,
        )
        return self.required_parameter_definitions

    def get_variables(self) -> Dict[str, Any]:
        """Return a dictionary of variables available to the template.

        These variables will have been defined within `VARIABLES` or
        `self.defined_variables`. Any variable value that contains a lookup
        will have been resolved.

        .. deprecated:: 2.0.0
            Replaced by :attr:`variables`.

        Returns:
            Variables available to the template.

        Raises:
            UnresolvedBlueprintVariables: If variables are unresolved.

        """
        LOGGER.warning(
            "%s.get_variables is deprecated and will be removed in a future release",
            self.__class__.__name__,
        )
        return self.variables

    def import_mappings(self) -> None:
        """Import mappings from CFNgin config to the blueprint."""
        if not self.mappings:
            return

        for name, mapping in self.mappings.items():
            LOGGER.debug("adding mapping %s", name)
            self.template.add_mapping(name, mapping)

    def read_user_data(self, user_data_path: str) -> str:
        """Read and parse a user_data file.

        Args:
            user_data_path: Path to the userdata file.

        """
        raw_user_data = read_value_from_path(user_data_path)
        return parse_user_data(self.variables, raw_user_data, self.name)

    def render_template(self) -> Tuple[str, str]:
        """Render the Blueprint to a CloudFormation template."""
        self.import_mappings()
        self.create_template()
        if self.description:
            self.set_template_description(self.description)
        self.setup_parameters()
        rendered = self.template.to_json(indent=self.context.template_indent)
        version = hashlib.md5(rendered.encode()).hexdigest()[:8]
        return version, rendered

    def reset_template(self) -> None:
        """Reset template."""
        self.template = Template()
        self._rendered = None
        self._version = None

    def resolve_variables(self, provided_variables: List[Variable]) -> None:
        """Resolve the values of the blueprint variables.

        This will resolve the values of the `VARIABLES` with values from the
        env file, the config, and any lookups resolved.

        Args:
            provided_variables: List of provided variables.

        """
        self._resolved_variables = {}
        variable_dict = {var.name: var for var in provided_variables}
        for var_name, var_def in self.defined_variables.items():
            value = resolve_variable(
                var_name, var_def, variable_dict.get(var_name), self.name
            )
            self._resolved_variables[var_name] = value

    def set_template_description(self, description: str) -> None:
        """Add a description to the Template.

        Args:
            description: A description to be added to the resulting template.

        """
        self.template.set_description(description)

    def setup_parameters(self) -> None:
        """Add any CloudFormation parameters to the template."""
        template = self.template

        if not self.parameter_definitions:
            LOGGER.debug("no parameters defined")
            return

        for name, attrs in self.parameter_definitions.items():
            built_param = build_parameter(name, attrs)
            template.add_parameter(built_param)

    def to_json(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """Render the blueprint and return the template in json form.

        Args:
            variables: Dictionary providing/overriding variable values.

        """
        variables_to_resolve: List[Variable] = []
        if variables:
            for key, value in variables.items():
                variables_to_resolve.append(Variable(key, value, "cfngin"))
        for k in self.parameter_definitions:
            if not variables or k not in variables:
                # The provided value for a CFN parameter has no effect in this
                # context (generating the CFN template), so any string can be
                # provided for its value - just needs to be something
                variables_to_resolve.append(Variable(k, "unused_value", "cfngin"))
        self.resolve_variables(variables_to_resolve)

        return self.render_template()[1]
