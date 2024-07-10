"""Tests for runway.cfngin.blueprints.base."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Union

import pytest
from mock import Mock
from troposphere import Parameter, Ref, s3, sns

from runway.cfngin.blueprints.base import (
    Blueprint,
    CFNParameter,
    build_parameter,
    parse_user_data,
    resolve_variable,
    validate_allowed_values,
    validate_variable_type,
)
from runway.cfngin.blueprints.variables.types import (
    CFNCommaDelimitedList,
    CFNNumber,
    CFNString,
    TroposphereType,
)
from runway.cfngin.exceptions import (
    InvalidUserdataPlaceholder,
    MissingVariable,
    UnresolvedBlueprintVariable,
    UnresolvedBlueprintVariables,
    ValidatorError,
    VariableTypeRequired,
)
from runway.variables import Variable

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef
    from runway.context import CfnginContext

MODULE = "runway.cfngin.blueprints.base"


class SampleBlueprint(Blueprint):
    """Sample Blueprint to use for testing."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
        "Var0": {"type": CFNString, "default": "test"},
        "Var1": {"type": str, "default": ""},
    }

    def create_template(self) -> None:
        """Create template."""
        return None


def resolve_troposphere_var(tpe: Any, value: Any, **kwargs: Any) -> Any:
    """Resolve troposphere var."""
    return resolve_variable(
        "name",
        {"type": TroposphereType(tpe, **kwargs)},
        Variable("name", value, "cfngin"),
        "test",
    )


class TestBlueprint:
    """Test Blueprint."""

    def test_add_output(self, cfngin_context: CfnginContext) -> None:
        """Test add_output."""
        output_name = "MyOutput1"
        output_value = "OutputValue"

        class _Blueprint(Blueprint):
            def create_template(self) -> None:
                """Create template."""
                self.template.set_version("2010-09-09")
                self.template.set_description("TestBlueprint")
                self.add_output(output_name, output_value)

        blueprint = _Blueprint(name="test", context=cfngin_context)
        blueprint.render_template()
        assert blueprint.template.outputs[output_name].properties["Value"] == output_value

    def test_cfn_parameters(self, cfngin_context: CfnginContext) -> None:
        """Test cfn_parameters."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        obj.resolve_variables([])
        assert obj.cfn_parameters == {"Var0": "test"}

    def test_create_template(self, cfngin_context: CfnginContext) -> None:
        """Test create_template."""
        with pytest.raises(NotImplementedError):
            Blueprint(name="test", context=cfngin_context).create_template()

    def test_defined_variables(self, cfngin_context: CfnginContext) -> None:
        """Test defined_variables."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        assert obj.defined_variables == obj.VARIABLES
        assert id(obj.defined_variables) != obj.VARIABLES

    def test_description(self, cfngin_context: CfnginContext) -> None:
        """Test description."""
        description = "my blueprint description"
        obj = SampleBlueprint(name="test", context=cfngin_context, description=description)
        assert obj.description == description
        obj.render_template()
        assert obj.template.description == description

    def test_get_cfn_parameters(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test get_cfn_parameters."""
        mock_cfn_parameters = mocker.patch.object(Blueprint, "cfn_parameters", "success")
        assert (
            Blueprint(name="test", context=cfngin_context).get_cfn_parameters()
            == mock_cfn_parameters
        )

    def test_get_output_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test get_output_definitions."""
        mock_output_definitions = mocker.patch.object(Blueprint, "output_definitions", "success")
        assert (
            Blueprint(name="test", context=cfngin_context).get_output_definitions()
            == mock_output_definitions
        )

    def test_get_parameter_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test get_parameter_definitions."""
        mock_parameter_definitions = mocker.patch.object(
            Blueprint, "parameter_definitions", "success"
        )
        assert (
            Blueprint(name="test", context=cfngin_context).get_parameter_definitions()
            == mock_parameter_definitions
        )

    def test_get_parameter_values(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test get_parameter_values."""
        mock_parameter_values = mocker.patch.object(Blueprint, "parameter_values", "success")
        assert (
            Blueprint(name="test", context=cfngin_context).get_parameter_values()
            == mock_parameter_values
        )

    def test_get_required_parameter_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test get_required_parameter_definitions."""
        mock_required_parameter_definitions = mocker.patch.object(
            Blueprint, "required_parameter_definitions", "success"
        )
        assert (
            Blueprint(name="test", context=cfngin_context).get_required_parameter_definitions()
            == mock_required_parameter_definitions
        )

    def test_get_variables(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test get_variables."""
        mock_variables = mocker.patch.object(Blueprint, "variables", "success")
        assert Blueprint(name="test", context=cfngin_context).get_variables() == mock_variables

    def test_init_raise_attribute_error(self, cfngin_context: CfnginContext) -> None:
        """Test __init__."""

        class _Blueprint(Blueprint):
            PARAMETERS: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {}

            def create_template(self) -> None:
                """Create template."""
                return None

        with pytest.raises(AttributeError):
            _Blueprint("test", cfngin_context)

    def test_output_definitions(self, cfngin_context: CfnginContext) -> None:
        """Test output_definitions."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        assert obj.output_definitions == {}
        obj.add_output("key", "val")
        assert obj.output_definitions == {"key": {"Value": "val"}}

    def test_parameter_definitions(self, cfngin_context: CfnginContext) -> None:
        """Test parameter_definitions."""
        assert SampleBlueprint(name="test", context=cfngin_context).parameter_definitions == {
            "Var0": {"type": "String", "default": "test"}
        }

    def test_parameter_values(self, cfngin_context: CfnginContext) -> None:
        """Test parameter_values."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        obj.resolve_variables([])
        assert obj.parameter_values == {"Var0": "test"}

    def test_read_user_data(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test read_user_data."""
        mock_read_value_from_path = mocker.patch(
            f"{MODULE}.read_value_from_path", return_value="something"
        )
        mock_parse_user_data = mocker.patch(f"{MODULE}.parse_user_data", return_value="success")
        obj = SampleBlueprint(name="test", context=cfngin_context)
        obj.resolve_variables([])
        assert obj.read_user_data("path") == mock_parse_user_data.return_value
        mock_read_value_from_path.assert_called_once_with("path")
        mock_parse_user_data.assert_called_once_with(
            obj.variables, mock_read_value_from_path.return_value, obj.name
        )

    def test_rendered(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test rendered."""
        mock_render_template = mocker.patch.object(
            SampleBlueprint, "render_template", return_value=("version", "render")
        )
        obj = SampleBlueprint(name="test", context=cfngin_context)
        assert obj.rendered == "render"
        mock_render_template.assert_called_once_with()

    def test_required_parameter_definitions(self, cfngin_context: CfnginContext) -> None:
        """Test required_parameter_definitions."""

        class _Blueprint(SampleBlueprint):
            VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
                "Var0": {"type": CFNString},
                "Var1": {"type": str, "default": ""},
            }

        assert _Blueprint(name="test", context=cfngin_context).required_parameter_definitions == {
            "Var0": {"type": "String"}
        }

    def test_required_parameter_definitions_none(self, cfngin_context: CfnginContext) -> None:
        """Test required_parameter_definitions."""
        assert SampleBlueprint(name="test", context=cfngin_context).required_parameter_definitions

    def test_reset_template(self, cfngin_context: CfnginContext) -> None:
        """Test reset_template."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        obj._rendered = "true"
        obj._version = "test"
        initial_template = obj.template
        assert not obj.reset_template()
        assert id(obj.template) != id(initial_template)
        assert obj._rendered is None
        assert obj._version is None

    def test_requires_change_set(self, cfngin_context: CfnginContext) -> None:
        """Test requires_change_set."""
        obj = SampleBlueprint(name="test", context=cfngin_context)
        assert not obj.requires_change_set
        obj.template.transform = "something"  # type: ignore
        assert obj.requires_change_set

    def test_setup_parameters(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test setup_parameters."""
        template = Mock()
        mocker.patch(f"{MODULE}.build_parameter", return_value="params")
        obj = SampleBlueprint(name="test", context=cfngin_context, template=template)
        assert not obj.setup_parameters()
        template.add_parameter.assert_called_once_with("params")

    def test_to_json(self, cfngin_context: CfnginContext) -> None:
        """Test to_json."""

        class _Blueprint(Blueprint):
            VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
                "Param1": {"default": "default", "type": CFNString},
                "Param2": {"type": CFNNumber},
                "Param3": {"type": CFNCommaDelimitedList},
                "Param4": {"default": "foo", "type": str},
                "Param5": {"default": 5, "type": int},
            }

            def create_template(self) -> None:
                """Create template."""
                self.template.set_version("2010-09-09")
                self.template.set_description("TestBlueprint")

        result = _Blueprint("test", context=cfngin_context).to_json({"Param3": "something"})
        assert isinstance(result, str)
        assert json.loads(result) == {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "TestBlueprint",
            "Parameters": {
                "Param1": {"Default": "default", "Type": "String"},
                "Param2": {"Type": "Number"},
                "Param3": {"Type": "CommaDelimitedList"},
            },
            "Resources": {},
        }

    def test_mappings(self, cfngin_context: CfnginContext) -> None:
        """Test mappings."""
        mappings = {"Mapping": {"Test": True}}
        obj = SampleBlueprint(name="test", context=cfngin_context, mappings=mappings)
        assert obj.mappings == mappings
        obj.render_template()
        assert obj.template.mappings == mappings

    def test_variables(self, cfngin_context: CfnginContext) -> None:
        """Test variables."""

        class _Blueprint(Blueprint):
            VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {"Var0": {"type": str}}

            def create_template(self) -> None:
                """Create template."""

        obj = _Blueprint("test", cfngin_context)
        with pytest.raises(UnresolvedBlueprintVariables):
            _ = obj.variables
        obj.resolve_variables([Variable("Var0", "test")])
        assert obj.variables == {"Var0": "test"}
        obj.variables = {"key": "val"}
        assert obj.variables == {"key": "val"}

    def test_version(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test version."""
        mock_render_template = mocker.patch.object(
            SampleBlueprint, "render_template", return_value=("version", "render")
        )
        obj = SampleBlueprint(name="test", context=cfngin_context)
        assert obj.version == "version"
        mock_render_template.assert_called_once_with()


class TestCFNParameter:
    """Test CFNParameter."""

    def test_ref(self) -> None:
        """Test ref."""
        param = CFNParameter("name", "val")
        assert isinstance(param.ref, Ref)
        assert param.ref.data == {"Ref": "name"}

    def test_repr(self) -> None:
        """Test __repr__."""
        assert repr(CFNParameter("name", "val")) == "CFNParameter[name: val]"

    def test_to_parameter_value(self) -> None:
        """Test to_parameter_value."""
        # right now, this just returns :attr:`CFNParameter.value`
        assert CFNParameter("name", "val").to_parameter_value() == "val"

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("test", "test"),
            (["t0", "t1"], ["t0", "t1"]),
            (True, "true"),
            (False, "false"),
            (0, "0"),
            (1, "1"),
        ],
    )
    def test_value(self, expected: Union[List[str], str], provided: Any) -> None:
        """Test value."""
        assert CFNParameter("myParameter", provided).value == expected

    @pytest.mark.parametrize("provided", [({"key": "val"}), ({"t0", "t1"}), (None)])
    def test_value_raise_type_error(self, provided: Any) -> None:
        """Test value."""
        with pytest.raises(TypeError):
            CFNParameter("myParameter", provided)


def test_build_parameter() -> None:
    """Test build_parameter."""
    param = build_parameter("BasicParam", {"type": "String", "description": "test"})
    assert isinstance(param, Parameter)
    assert param.title == "BasicParam"
    assert param.Type == "String"
    assert param.Description == "test"


def test_parse_user_data() -> None:
    """Test parse_user_data."""
    assert (
        parse_user_data(
            {"name": CFNParameter("name", "tom"), "last": "smith"},
            "name: ${name}, last: $last and $$",
            "test",
        )
        == "name: tom, last: smith and $"
    )


def test_parse_user_data_raise_invalid_placeholder() -> None:
    """Test parse_user_data."""
    with pytest.raises(InvalidUserdataPlaceholder):
        parse_user_data({}, "$100", "test")


def test_parse_user_data_raise_missing_variable() -> None:
    """Test parse_user_data."""
    with pytest.raises(MissingVariable):
        parse_user_data({"name": "tom"}, "name: ${name}, last: $last and $$", "test")


def test_resolve_variable_allowed_values() -> None:
    """Test resolve_variable."""
    var_name = "testVar"
    var_def: BlueprintVariableTypeDef = {"type": str, "allowed_values": ["allowed"]}
    with pytest.raises(ValueError):
        resolve_variable(var_name, var_def, Variable(var_name, "not_allowed", "cfngin"), "test")
    assert (
        resolve_variable(var_name, var_def, Variable(var_name, "allowed", "cfngin"), "test")
        == "allowed"
    )


def test_resolve_variable_default() -> None:
    """Test resolve_variable."""
    default_value = "foo"
    assert (
        resolve_variable("name", {"default": default_value, "type": str}, None, "test")
        == default_value
    )


def test_resolve_variable_missing_variable() -> None:
    """Test resolve_variable raise MissingVariable."""
    with pytest.raises(MissingVariable):
        resolve_variable("name", {"type": str}, None, "test")


def test_resolve_variable_no_type() -> None:
    """Test resolve_variable."""
    with pytest.raises(VariableTypeRequired):
        resolve_variable("name", {}, None, "test")


def test_resolve_variable_provided_not_resolved(mocker: MockerFixture) -> None:
    """Test resolve_variable."""
    mocker.patch("runway.variables.CFNGIN_LOOKUP_HANDLERS", {"mock": Mock()})
    with pytest.raises(UnresolvedBlueprintVariable):
        resolve_variable("name", {"type": str}, Variable("name", "${mock abc}", "cfngin"), "test")


def test_resolve_variable_troposphere_fail() -> None:
    """Test resolve_variable."""
    with pytest.raises(ValidatorError):
        resolve_troposphere_var(s3.Bucket, {"MyBucket": {"BucketName": 1}})


def test_resolve_variable_troposphere_fail_prop() -> None:
    """Test resolve_variable."""
    with pytest.raises(ValidatorError):
        resolve_troposphere_var(sns.Subscription, {})


def test_resolve_variable_troposphere_many() -> None:
    """Test resolve_variable."""
    bucket_defs = {
        "FirstBucket": {"BucketName": "some-bucket"},
        "SecondBucket": {"BucketName": "some-other-bucket"},
    }
    buckets = resolve_troposphere_var(s3.Bucket, bucket_defs, many=True)
    for bucket in buckets:
        assert isinstance(bucket, s3.Bucket)
        assert bucket.properties == bucket_defs[bucket.title]


def test_resolve_variable_troposphere_many_empty() -> None:
    """Test resolve_variable."""
    assert resolve_troposphere_var(s3.Bucket, {}, many=True) == []


def test_resolve_variable_troposphere_many_optional_empty() -> None:
    """Test resolve_variable."""
    assert resolve_troposphere_var(s3.Bucket, {}, many=True, optional=True) is None


def test_resolve_variable_troposphere_many_props() -> None:
    """Test resolve_variable."""
    sub_defs = [
        {"Endpoint": "test1", "Protocol": "lambda"},
        {"Endpoint": "test2", "Protocol": "lambda"},
    ]
    subs = resolve_troposphere_var(sns.Subscription, sub_defs, many=True)

    for i, sub in enumerate(subs):
        assert isinstance(sub, sns.Subscription)
        assert sub.properties == sub_defs[i]


def test_resolve_variable_troposphere_many_props_empty() -> None:
    """Test resolve_variable."""
    assert resolve_troposphere_var(sns.Subscription, [], many=True) == []


def test_resolve_variable_troposphere_not_validated() -> None:
    """Test resolve_variable."""
    resolve_troposphere_var(sns.Subscription, {}, validate=False)


def test_resolve_variable_troposphere_optional() -> None:
    """Test resolve_variable."""
    assert not resolve_troposphere_var(s3.Bucket, None, optional=True)


def test_resolve_variable_troposphere_optional_prop() -> None:
    """Test resolve_variable."""
    assert not resolve_troposphere_var(sns.Subscription, None, optional=True)


def test_resolve_variable_troposphere_raise_value_error() -> None:
    """Test resolve_variable."""
    with pytest.raises(ValidatorError):
        resolve_troposphere_var(s3.Bucket, None)


def test_resolve_variable_troposphere_single() -> None:
    """Test resolve_variable."""
    bucket_defs = {"MyBucket": {"BucketName": "some-bucket"}}
    bucket = resolve_troposphere_var(s3.Bucket, bucket_defs)
    assert isinstance(bucket, s3.Bucket)
    assert bucket.properties == bucket_defs[bucket.title]
    assert bucket.title == "MyBucket"


def test_resolve_variable_troposphere_single_prop() -> None:
    """Test resolve_variable."""
    sub_defs = {"Endpoint": "test", "Protocol": "lambda"}
    sub = resolve_troposphere_var(sns.Subscription, sub_defs)
    assert isinstance(sub, sns.Subscription)
    assert sub.properties == sub_defs


def test_resolve_variable_validator_invalid_value() -> None:
    """Test resolve_variable."""

    def triple_validator(value: Any) -> Any:
        if len(value) != 3:
            raise ValueError("Must be a triple.")
        return value

    var_name = "testVar"
    var_value = [1, 2]
    with pytest.raises(ValidatorError) as exc:
        resolve_variable(
            var_name,
            {"type": list, "validator": triple_validator},
            Variable(var_name, var_value, "cfngin"),
            "",
        )
    assert isinstance(exc.value.exception, ValueError)


def test_resolve_variable_validator_valid_value() -> None:
    """Test resolve_variable."""

    def triple_validator(value: Any) -> Any:
        if len(value) != 3:
            raise ValueError
        return value

    var_name = "testVar"
    var_value = [1, 2, 3]
    assert (
        resolve_variable(
            var_name,
            {"type": list, "validator": triple_validator},
            Variable(var_name, var_value, "cfngin"),
            "test",
        )
        == var_value
    )


def test_validate_allowed_values() -> None:
    """Test validate allowed values."""
    assert validate_allowed_values([], "not_allowed")
    assert not validate_allowed_values(["allowed"], "not_allowed")
    assert validate_allowed_values(["allowed"], "allowed")


def test_validate_variable_type_cfn() -> None:
    """Test validate_variable_type."""
    result = validate_variable_type("name", CFNString, "test")
    assert isinstance(result, CFNParameter)
    assert result.name == "name"
    assert result.value == "test"


def test_validate_variable_type_cfn_raise_type_error() -> None:
    """Test validate_variable_type."""
    with pytest.raises(TypeError):
        validate_variable_type("name", CFNString, None)


def test_validate_variable_type_python() -> None:
    """Test validate_variable_type."""
    assert validate_variable_type("name", str, "test") == "test"


def test_validate_variable_type_python_raise_type_error() -> None:
    """Test validate_variable_type."""
    with pytest.raises(TypeError):
        validate_variable_type("name", int, "0")


def test_validate_variable_type_troposphere(mocker: MockerFixture) -> None:
    """Test validate_variable_type."""
    mock_create = mocker.patch.object(TroposphereType, "create", side_effect=["success", Exception])
    value = {"Endpoint": "test", "Protocol": "test"}
    assert validate_variable_type("test", TroposphereType(sns.Subscription), value) == "success"
    mock_create.assert_called_once_with(value)
    with pytest.raises(ValidatorError):
        validate_variable_type("test", TroposphereType(sns.Subscription), value)
