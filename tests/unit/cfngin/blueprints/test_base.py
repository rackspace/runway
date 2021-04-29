"""Tests for runway.cfngin.blueprints.base."""
# pylint: disable=abstract-method,arguments-differ,no-self-use,protected-access,unused-argument
# pyright: basic
from __future__ import annotations

import sys
import unittest
from typing import TYPE_CHECKING, Any, Dict, cast

from mock import MagicMock, patch
from troposphere import Base64, Ref, s3, sns

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
    EC2AvailabilityZoneNameList,
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
from runway.cfngin.lookups.registry import (
    register_lookup_handler,
    unregister_lookup_handler,
)
from runway.exceptions import InvalidLookupConcatenation
from runway.lookups.handlers.base import LookupHandler
from runway.variables import Variable

from ..factories import mock_context

if TYPE_CHECKING:
    from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


def mock_lookup_handler(value: str, **_: Any) -> str:
    """Mock lookup handler."""
    return value


class MockLookupHandler(LookupHandler):
    """Mock lookup handler."""

    @classmethod
    def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> Any:  # type: ignore
        """Perform the lookup."""
        return value


register_lookup_handler("mock", MockLookupHandler)


class TestBuildParameter(unittest.TestCase):
    """Tests for runway.cfngin.blueprints.base.build_parameter."""

    def test_base_parameter(self) -> None:
        """Test base parameter."""
        param = build_parameter("BasicParam", {"type": "String"})
        param.validate()
        self.assertEqual(param.Type, "String")


class TestBlueprintRendering(unittest.TestCase):
    """Tests for runway.cfngin.blueprints.base.Blueprint rendering."""

    def test_to_json(self) -> None:
        """Test to json."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"default": "default", "type": CFNString},
                "Param2": {"type": CFNNumber},
                "Param3": {"type": CFNCommaDelimitedList},
                "Param4": {"default": "foo", "type": str},
                "Param5": {"default": 5, "type": int},
            }

            def create_template(self) -> None:
                """Create template."""
                self.template.add_version("2010-09-09")
                self.template.add_description("TestBlueprint")

        expected_json = """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "TestBlueprint",
    "Parameters": {
        "Param1": {
            "Default": "default",
            "Type": "String"
        },
        "Param2": {
            "Type": "Number"
        },
        "Param3": {
            "Type": "CommaDelimitedList"
        }
    },
    "Resources": {}
}"""
        self.assertEqual(
            TestBlueprint(name="test", context=mock_context()).to_json(), expected_json,
        )


class TestBaseBlueprint(unittest.TestCase):
    """Tests for runway.cfngin.blueprints.base.Blueprint."""

    def test_add_output(self) -> None:
        """Test add output."""
        output_name = "MyOutput1"
        output_value = "OutputValue"

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {}

            def create_template(self) -> None:
                """Create template."""
                self.template.add_version("2010-09-09")
                self.template.add_description("TestBlueprint")
                self.add_output(output_name, output_value)

        blueprint = TestBlueprint(name="test", context=mock_context())
        blueprint.render_template()
        self.assertEqual(
            blueprint.template.outputs[output_name].properties["Value"], output_value
        )


class TestVariables(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """Tests for runway.cfngin.blueprints.base.Blueprint variables."""

    def setUp(self) -> None:
        """Run before tests."""
        register_lookup_handler("mock", MockLookupHandler)
        return super().setUp()

    def tearDown(self) -> None:
        """Run after tests."""
        unregister_lookup_handler("custom")
        unregister_lookup_handler("mock")
        return super().tearDown()

    def test_defined_variables(self) -> None:
        """Test defined variables."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES: Dict[str, BlueprintVariableTypeDef] = {
                "Param1": {"default": "default", "type": str},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        self.assertEqual(
            blueprint.defined_variables(), blueprint.VARIABLES,
        )

    def test_defined_variables_subclass(self) -> None:
        """Test defined variables subclass."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES: Dict[str, BlueprintVariableTypeDef] = {
                "Param1": {"default": 0, "type": int},
                "Param2": {"default": 0, "type": int},
            }

        class TestBlueprintSubclass(TestBlueprint):
            """Test blueprint subclass."""

            def defined_variables(self) -> Dict[str, BlueprintVariableTypeDef]:
                """Return defined variables."""
                variables = super().defined_variables()
                variables["Param2"]["default"] = 1
                variables["Param3"] = cast(
                    "BlueprintVariableTypeDef", {"default": 1, "type": int}
                )
                return variables

        blueprint = TestBlueprintSubclass(name="test", context=MagicMock())
        variables = blueprint.defined_variables()
        self.assertEqual(len(variables), 3)
        self.assertEqual(variables["Param2"]["default"], 1)

    def test_get_variables_unresolved_variables(self) -> None:
        """Test get variables unresolved variables."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

        blueprint = TestBlueprint(name="test", context=MagicMock())
        with self.assertRaises(UnresolvedBlueprintVariables):
            blueprint.get_variables()

    def test_set_description(self) -> None:
        """Test set description."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"default": "default", "type": str},
            }

            def create_template(self) -> None:
                """Create template."""
                return

        description = "my blueprint description"
        context = mock_context()
        blueprint = TestBlueprint(name="test", context=context, description=description)
        blueprint.render_template()
        self.assertEqual(description, blueprint.template.description)

    def test_validate_variable_type_cfntype(self) -> None:
        """Test validate variable type cfntype."""
        var_name = "testVar"
        var_type = CFNString
        provided_value = "abc"
        value = validate_variable_type(var_name, var_type, provided_value)
        self.assertIsInstance(value, CFNParameter)

    def test_validate_variable_type_cfntype_none_value(self) -> None:
        """Test validate variable type cfntype none value."""
        with self.assertRaises(ValueError):
            var_name = "testVar"
            var_type = CFNString
            provided_value = None
            validate_variable_type(var_name, var_type, provided_value)

    def test_validate_variable_type_matching_type(self) -> None:
        """Test validate variable type matching type."""
        var_name = "testVar"
        var_type = str
        provided_value = "abc"
        value = validate_variable_type(var_name, var_type, provided_value)
        self.assertEqual(value, provided_value)

    def test_strict_validate_variable_type(self) -> None:
        """Test strict validate variable type."""
        with self.assertRaises(ValueError):
            var_name = "testVar"
            var_type = int
            provided_value = "1"
            validate_variable_type(var_name, var_type, provided_value)

    def test_validate_variable_type_invalid_value(self) -> None:
        """Test validate variable type invalid value."""
        with self.assertRaises(ValueError):
            var_name = "testVar"
            var_type = int
            provided_value = "abc"
            validate_variable_type(var_name, var_type, provided_value)

    def test_resolve_variable_no_type_on_variable_definition(self) -> None:
        """Test resolve variable no type on variable definition."""
        with self.assertRaises(VariableTypeRequired):
            var_name = "testVar"
            var_def: Dict[str, Any] = {}
            provided_variable = None
            blueprint_name = "testBlueprint"

            resolve_variable(
                var_name, var_def, provided_variable, blueprint_name  # type: ignore
            )

    def test_resolve_variable_no_provided_with_default(self) -> None:
        """Test resolve variable no provided with default."""
        var_name = "testVar"
        default_value = "foo"
        var_def: BlueprintVariableTypeDef = {"default": default_value, "type": str}
        provided_variable = None
        blueprint_name = "testBlueprint"

        value = resolve_variable(var_name, var_def, provided_variable, blueprint_name)

        self.assertEqual(default_value, value)

    def test_resolve_variable_no_provided_without_default(self) -> None:
        """Test resolve variable no provided without default."""
        with self.assertRaises(MissingVariable):
            var_name = "testVar"
            var_def: BlueprintVariableTypeDef = {"type": str}
            provided_variable = None
            blueprint_name = "testBlueprint"

            resolve_variable(var_name, var_def, provided_variable, blueprint_name)

    def test_resolve_variable_provided_not_resolved(self) -> None:
        """Test resolve variable provided not resolved."""
        var_name = "testVar"
        provided_variable = Variable(var_name, "${mock abc}", "cfngin")
        with self.assertRaises(UnresolvedBlueprintVariable):
            var_def: BlueprintVariableTypeDef = {"type": str}
            blueprint_name = "testBlueprint"

            resolve_variable(var_name, var_def, provided_variable, blueprint_name)

    def _resolve_troposphere_var(self, tpe: Any, value: Any, **kwargs: Any) -> Any:
        """Resolve troposphere var."""
        var_name = "testVar"
        var_def: BlueprintVariableTypeDef = {"type": TroposphereType(tpe, **kwargs)}
        provided_variable = Variable(var_name, value, "cfngin")
        blueprint_name = "testBlueprint"

        return resolve_variable(var_name, var_def, provided_variable, blueprint_name)

    def test_resolve_variable_troposphere_type_resource_single(self) -> None:
        """Test resolve variable troposphere type resource single."""
        bucket_defs = {"MyBucket": {"BucketName": "some-bucket"}}
        bucket = self._resolve_troposphere_var(s3.Bucket, bucket_defs)

        self.assertTrue(isinstance(bucket, s3.Bucket))
        self.assertEqual(bucket.properties, bucket_defs[bucket.title])
        self.assertEqual(bucket.title, "MyBucket")

    def test_resolve_variable_troposphere_type_resource_optional(self) -> None:
        """Test resolve variable troposphere type resource optional."""
        bucket = self._resolve_troposphere_var(s3.Bucket, None, optional=True)
        self.assertEqual(bucket, None)

    def test_resolve_variable_troposphere_type_value_blank_required(self) -> None:
        """Test resolve variable troposphere type value blank required."""
        with self.assertRaises(ValidatorError):
            self._resolve_troposphere_var(s3.Bucket, None)

    def test_resolve_variable_troposphere_type_resource_many(self) -> None:
        """Test resolve variable troposphere type resource many."""
        bucket_defs = {
            "FirstBucket": {"BucketName": "some-bucket"},
            "SecondBucket": {"BucketName": "some-other-bucket"},
        }
        buckets = self._resolve_troposphere_var(s3.Bucket, bucket_defs, many=True)

        for bucket in buckets:
            self.assertTrue(isinstance(bucket, s3.Bucket))
            self.assertEqual(bucket.properties, bucket_defs[bucket.title])

    def test_resolve_variable_troposphere_type_resource_many_empty(self) -> None:
        """Test resolve variable troposphere type resource many empty."""
        buckets = self._resolve_troposphere_var(s3.Bucket, {}, many=True)
        self.assertEqual(buckets, [])

    def test_resolve_variable_troposphere_type_resource_fail(self) -> None:
        """Test resolve variable troposphere type resource fail."""
        # Do this to silence the error reporting here:
        # https://github.com/cloudtools/troposphere/commit/dc8abd5c
        with open("/dev/null", "w") as devnull:
            _stderr = sys.stderr
            sys.stderr = devnull
            with self.assertRaises(ValidatorError):
                self._resolve_troposphere_var(
                    s3.Bucket, {"MyBucket": {"BucketName": 1}}
                )
            sys.stderr = _stderr

    def test_resolve_variable_troposphere_type_props_single(self) -> None:
        """Test resolve variable troposphere type props single."""
        sub_defs = {"Endpoint": "test", "Protocol": "lambda"}
        # Note that sns.Subscription != sns.SubscriptionResource. The former
        # is a property type, the latter is a complete resource.
        sub = self._resolve_troposphere_var(sns.Subscription, sub_defs)

        self.assertTrue(isinstance(sub, sns.Subscription))
        self.assertEqual(sub.properties, sub_defs)

    def test_resolve_variable_troposphere_type_props_optional(self) -> None:
        """Test resolve variable troposphere type props optional."""
        sub = self._resolve_troposphere_var(sns.Subscription, None, optional=True)
        self.assertEqual(sub, None)

    def test_resolve_variable_troposphere_type_props_many(self) -> None:
        """Test resolve variable troposphere type props many."""
        sub_defs = [
            {"Endpoint": "test1", "Protocol": "lambda"},
            {"Endpoint": "test2", "Protocol": "lambda"},
        ]
        subs = self._resolve_troposphere_var(sns.Subscription, sub_defs, many=True)

        for i, sub in enumerate(subs):
            self.assertTrue(isinstance(sub, sns.Subscription))
            self.assertEqual(sub.properties, sub_defs[i])

    def test_resolve_variable_troposphere_type_props_many_empty(self) -> None:
        """Test resolve variable troposphere type props many empty."""
        subs = self._resolve_troposphere_var(sns.Subscription, [], many=True)
        self.assertEqual(subs, [])

    def test_resolve_variable_troposphere_type_props_fail(self) -> None:
        """Test resolve variable troposphere type props fail."""
        with self.assertRaises(ValidatorError):
            self._resolve_troposphere_var(sns.Subscription, {})

    def test_resolve_variable_troposphere_type_not_validated(self) -> None:
        """Test resolve variable troposphere type not validated."""
        self._resolve_troposphere_var(sns.Subscription, {}, validate=False)

    def test_resolve_variable_troposphere_type_optional_many(self) -> None:
        """Test resolve variable troposphere type optional many."""
        res = self._resolve_troposphere_var(
            sns.Subscription, {}, many=True, optional=True
        )
        self.assertIsNone(res)

    def test_resolve_variable_provided_resolved(self) -> None:
        """Test resolve variable provided resolved."""
        var_name = "testVar"
        var_def: BlueprintVariableTypeDef = {"type": str}
        provided_variable = Variable(var_name, "${mock 1}", "cfngin")
        provided_variable.resolve(context=MagicMock(), provider=MagicMock())
        blueprint_name = "testBlueprint"

        value = resolve_variable(var_name, var_def, provided_variable, blueprint_name)
        self.assertEqual(value, "1")

    def test_resolve_variable_allowed_values(self) -> None:
        """Test resolve variable allowed values."""
        var_name = "testVar"
        var_def: BlueprintVariableTypeDef = {"type": str, "allowed_values": ["allowed"]}
        provided_variable = Variable(var_name, "not_allowed", "cfngin")
        blueprint_name = "testBlueprint"
        with self.assertRaises(ValueError):
            resolve_variable(var_name, var_def, provided_variable, blueprint_name)

        provided_variable = Variable(var_name, "allowed", "cfngin")
        value = resolve_variable(var_name, var_def, provided_variable, blueprint_name)
        self.assertEqual(value, "allowed")

    def test_resolve_variable_validator_valid_value(self) -> None:
        """Test resolve variable validator valid value."""

        def triple_validator(value: Any) -> Any:
            if len(value) != 3:
                raise ValueError
            return value

        var_name = "testVar"
        var_def: BlueprintVariableTypeDef = {
            "type": list,
            "validator": triple_validator,
        }
        var_value = [1, 2, 3]
        provided_variable = Variable(var_name, var_value, "cfngin")
        blueprint_name = "testBlueprint"

        value = resolve_variable(var_name, var_def, provided_variable, blueprint_name)
        self.assertEqual(value, var_value)

    def test_resolve_variable_validator_invalid_value(self) -> None:
        """Test resolve variable validator invalid value."""

        def triple_validator(value: Any) -> Any:
            if len(value) != 3:
                raise ValueError("Must be a triple.")
            return value

        var_name = "testVar"
        var_def: BlueprintVariableTypeDef = {
            "type": list,
            "validator": triple_validator,
        }
        var_value = [1, 2]
        provided_variable = Variable(var_name, var_value, "cfngin")
        blueprint_name = "testBlueprint"

        with self.assertRaises(ValidatorError) as result:
            resolve_variable(var_name, var_def, provided_variable, blueprint_name)

        exc = result.exception.exception  # The wrapped exception
        self.assertIsInstance(exc, ValueError)

    def test_resolve_variables(self) -> None:
        """Test resolve variables."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"default": 0, "type": int},
                "Param2": {"type": str},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [
            Variable("Param1", 1, "cfngin"),
            Variable("Param2", "${output other-stack::Output}", "cfngin"),
            Variable("Param3", 3, "cfngin"),
        ]

        variables[1]._value._resolve("Test Output")

        blueprint.resolve_variables(variables)
        self.assertEqual(blueprint._resolved_variables["Param1"], 1)  # type: ignore
        self.assertEqual(blueprint._resolved_variables["Param2"], "Test Output")  # type: ignore
        self.assertIsNone(blueprint._resolved_variables.get("Param3"))  # type: ignore

    def test_resolve_variables_lookup_returns_non_string(self) -> None:
        """Test resolve variables lookup returns non string."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": list},
            }

        class FakeLookup(LookupHandler):
            """False Lookup."""

            @classmethod
            def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> Any:  # type: ignore
                """Perform the lookup."""
                return ["something"]

        register_lookup_handler("custom", FakeLookup)
        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", "${custom non-string-return-val}", "cfngin")]
        for var in variables:
            var._value.resolve({}, {})  # type: ignore

        blueprint.resolve_variables(variables)
        self.assertEqual(blueprint._resolved_variables["Param1"], ["something"])  # type: ignore

    def test_resolve_variables_lookup_returns_troposphere_obj(self) -> None:
        """Test resolve variables lookup returns troposphere obj."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": Base64},
            }

        class FakeLookup(LookupHandler):
            """False Lookup."""

            @classmethod
            def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> Any:  # type: ignore
                """Perform the lookup."""
                return Base64("test")

        register_lookup_handler("custom", FakeLookup)
        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", "${custom non-string-return-val}", "cfngin")]
        for var in variables:
            var._value.resolve({}, {})  # type: ignore

        blueprint.resolve_variables(variables)
        self.assertEqual(
            blueprint._resolved_variables["Param1"].data, Base64("test").data  # type: ignore
        )

    def test_resolve_variables_lookup_returns_non_string_invalid_combo(self) -> None:
        """Test resolve variables lookup returns non string invalid combo."""

        class FakeLookup(LookupHandler):
            """False Lookup."""

            @classmethod
            def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> Any:  # type: ignore
                """Perform the lookup."""
                return ["something"]

        register_lookup_handler("custom", FakeLookup)
        variable = Variable(
            "Param1",
            "${custom non-string-return-val},${output some-stack::Output}",
            "cfngin",
        )
        variable._value[0].resolve({}, {})  # type: ignore
        with self.assertRaises(InvalidLookupConcatenation):
            variable.value()  # pylint: disable=not-callable

    def test_get_variables(self) -> None:
        """Test get variables."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int},
                "Param2": {"type": str},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [
            Variable("Param1", 1, "cfngin"),
            Variable("Param2", "Test Output", "cfngin"),
        ]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertEqual(variables["Param1"], 1)
        self.assertEqual(variables["Param2"], "Test Output")

    def test_resolve_variables_missing_variable(self) -> None:
        """Test resolve variables missing variable."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int},
                "Param2": {"type": str},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", 1, "cfngin")]
        with self.assertRaises(MissingVariable):
            blueprint.resolve_variables(variables)

    def test_resolve_variables_incorrect_type(self) -> None:
        """Test resolve variables incorrect type."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", "Something", "cfngin")]
        with self.assertRaises(ValueError):
            blueprint.resolve_variables(variables)

    def test_get_variables_default_value(self) -> None:
        """Test get variables default value."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int, "default": 1},
                "Param2": {"type": str},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param2", "Test Output", "cfngin")]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertEqual(variables["Param1"], 1)
        self.assertEqual(variables["Param2"], "Test Output")

    def test_resolve_variables_convert_type(self) -> None:
        """Test resolve variables convert type."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", 1, "cfngin")]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertTrue(isinstance(variables["Param1"], int))

    def test_resolve_variables_cfn_type(self) -> None:
        """Test resolve variables cfn type."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": CFNString},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", "Value", "cfngin")]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertTrue(isinstance(variables["Param1"], CFNParameter))

    def test_resolve_variables_cfn_number(self) -> None:
        """Test resolve variables cfn number."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": CFNNumber},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", 1, "cfngin")]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertTrue(isinstance(variables["Param1"], CFNParameter))
        self.assertEqual(variables["Param1"].value, "1")

    def test_resolve_variables_cfn_type_list(self) -> None:
        """Test resolve variables cfn type list."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": EC2AvailabilityZoneNameList},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", ["us-east-1", "us-west-2"], "cfngin")]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertTrue(isinstance(variables["Param1"], CFNParameter))
        self.assertEqual(variables["Param1"].value, ["us-east-1", "us-west-2"])
        self.assertEqual(variables["Param1"].ref.data, Ref("Param1").data)
        parameters = blueprint.get_parameter_values()
        self.assertEqual(parameters["Param1"], ["us-east-1", "us-west-2"])

    def test_resolve_variables_cfn_type_list_invalid_value(self) -> None:
        """Test resolve variables cfn type list invalid value."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": EC2AvailabilityZoneNameList},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [Variable("Param1", {"main": "us-east-1"}, "cfngin")]
        with self.assertRaises(ValueError):
            blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()

    def test_get_parameter_definitions_cfn_type_list(self) -> None:
        """Test get parameter definitions cfn type list."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": EC2AvailabilityZoneNameList},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        parameters = blueprint.get_parameter_definitions()
        self.assertTrue("Param1" in parameters)
        parameter = parameters["Param1"]
        self.assertEqual(parameter["type"], "List<AWS::EC2::AvailabilityZone::Name>")

    def test_get_parameter_definitions_cfn_type(self) -> None:
        """Test get parameter definitions cfn type."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": CFNString},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        parameters = blueprint.get_parameter_definitions()
        self.assertTrue("Param1" in parameters)
        parameter = parameters["Param1"]
        self.assertEqual(parameter["type"], "String")

    def test_get_required_parameter_definitions_cfn_type(self) -> None:
        """Test get required parameter definitions cfn type."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": CFNString},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        blueprint.setup_parameters()
        params = blueprint.get_required_parameter_definitions()
        self.assertEqual(list(params.keys())[0], "Param1")

    def test_get_parameter_values(self) -> None:
        """Test get parameter values."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {
                "Param1": {"type": int},
                "Param2": {"type": CFNString},
            }

        blueprint = TestBlueprint(name="test", context=MagicMock())
        variables = [
            Variable("Param1", 1, "cfngin"),
            Variable("Param2", "Value", "cfngin"),
        ]
        blueprint.resolve_variables(variables)
        variables = blueprint.get_variables()
        self.assertEqual(len(variables), 2)
        parameters = blueprint.get_parameter_values()
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters["Param2"], "Value")

    def test_validate_allowed_values(self) -> None:
        """Test validate allowed values."""
        allowed_values = ["allowed"]
        valid = validate_allowed_values(allowed_values, "not_allowed")
        self.assertFalse(valid)
        valid = validate_allowed_values(allowed_values, "allowed")
        self.assertTrue(valid)

    def test_blueprint_with_parameters_fails(self) -> None:
        """Test blueprint with parameters fails."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            PARAMETERS = {
                "Param2": {"default": 0, "type": "Integer"},
            }

        with self.assertRaises(AttributeError):
            TestBlueprint(name="test", context=MagicMock())

        class TestBlueprint2(Blueprint):
            """Test blueprint."""

            LOCAL_PARAMETERS = {
                "Param2": {"default": 0, "type": "Integer"},
            }

        with self.assertRaises(AttributeError):
            TestBlueprint2(name="test", context=MagicMock())

    def test_variable_exists_but_value_is_none(self) -> None:
        """Test variable exists but value is none."""
        var_name = "testVar"
        var_value = None
        provided_variable = Variable(var_name, var_value, "cfngin")
        with self.assertRaises(ValueError):
            var_def: BlueprintVariableTypeDef = {"type": str}
            blueprint_name = "testBlueprint"

            resolve_variable(var_name, var_def, provided_variable, blueprint_name)


class TestCFNParameter(unittest.TestCase):
    """Tests for runway.cfngin.blueprints.base.CFNParameter."""

    def test_cfnparameter_convert_boolean(self) -> None:
        """Test cfnparameter convert boolean."""
        param = CFNParameter("myParameter", True)
        self.assertEqual(param.value, "true")
        param = CFNParameter("myParameter", False)
        self.assertEqual(param.value, "false")
        # Test to make sure other types aren't affected
        param = CFNParameter("myParameter", 0)
        self.assertEqual(param.value, "0")
        param = CFNParameter("myParameter", "myString")
        self.assertEqual(param.value, "myString")

    def test_parse_user_data(self) -> None:
        """Test parse user data."""
        expected = "name: tom, last: taubkin and $"
        variables = {"name": "tom", "last": "taubkin"}

        raw_user_data = "name: ${name}, last: $last and $$"
        blueprint_name = "test"
        res = parse_user_data(variables, raw_user_data, blueprint_name)
        self.assertEqual(res, expected)

    def test_parse_user_data_missing_variable(self) -> None:
        """Test parse user data missing variable."""
        with self.assertRaises(MissingVariable):
            variables = {
                "name": "tom",
            }

            raw_user_data = "name: ${name}, last: $last and $$"
            blueprint_name = "test"
            parse_user_data(variables, raw_user_data, blueprint_name)

    def test_parse_user_data_invalid_placeholder(self) -> None:
        """Test parse user data invalid placeholder."""
        with self.assertRaises(InvalidUserdataPlaceholder):
            raw_user_data = "$100"
            blueprint_name = "test"
            parse_user_data({}, raw_user_data, blueprint_name)

    @patch(
        "runway.cfngin.blueprints.base.read_value_from_path", return_value="contents"
    )
    @patch("runway.cfngin.blueprints.base.parse_user_data")
    def test_read_user_data(self, parse_mock: MagicMock, file_mock: MagicMock) -> None:
        """Test read user data."""

        class TestBlueprint(Blueprint):
            """Test blueprint."""

            VARIABLES = {}

        blueprint = TestBlueprint(name="blueprint_name", context=MagicMock())
        blueprint.resolve_variables({})  # type: ignore
        blueprint.read_user_data("file://test.txt")
        file_mock.assert_called_with("file://test.txt")
        parse_mock.assert_called_with({}, "contents", "blueprint_name")
