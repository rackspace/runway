"""Test runway.lookups.handlers.ssm."""
# pylint: disable=no-self-use,unused-import
import json
from datetime import datetime

import pytest
import yaml

from runway.cfngin.exceptions import FailedVariableLookup
from runway.variables import Variable


def get_parameter_response(name, value, value_type="String", label=None, version=1):
    """Generate a mock ssm.get_parameter response."""
    selector = "{}/{}".format(name, label or version)
    return {
        "Parameter": {
            "Name": name,
            "Type": value_type,
            "Value": value,
            "Version": 1,
            "Selector": selector,
            "SourceResult": "",
            "LastModifiedDate": datetime.now(),
            "ARN": "",
        }
    }


def get_parameter_request(name, decrypt=True):
    """Generate the expected request paramters for ssm.get_parameter."""
    return {"Name": name, "WithDecryption": decrypt}


class TestSsmLookup(object):
    """Test runway.lookups.handlers.ssm.SsmLookup."""

    def test_basic(self, cfngin_context, runway_context):
        """Test resolution of a basic lookup."""
        name = "/test/param"
        value = "test value"
        cfngin_stubber = cfngin_context.add_stubber("ssm")
        runway_stubber = runway_context.add_stubber("ssm")
        cfngin_var = Variable("test_var", "${ssm %s}" % name, variable_type="cfngin")
        runway_var = Variable("test_var", "${ssm %s}" % name, variable_type="runway")

        for stubber in [cfngin_stubber, runway_stubber]:
            stubber.add_response(
                "get_parameter",
                get_parameter_response(name, value),
                get_parameter_request(name),
            )

        with cfngin_stubber as cfn_stub, runway_stubber as rw_stub:
            cfngin_var.resolve(context=cfngin_context)
            assert cfngin_var.value == value

            runway_var.resolve(context=runway_context)
            assert runway_var.value == value

        cfn_stub.assert_no_pending_responses()
        rw_stub.assert_no_pending_responses()

    def test_default(self, runway_context):
        """Test resolution of a default value."""
        name = "/test/param"
        value = "test value"
        stubber = runway_context.add_stubber("ssm")
        var = Variable(
            "test_var",
            "${ssm /test/invalid::load=json, default=${ssm %s}}" % name,
            variable_type="runway",
        )

        stubber.add_response(
            "get_parameter",
            get_parameter_response(name, value),
            get_parameter_request(name),
        )
        stubber.add_client_error(
            "get_parameter",
            "ParameterNotFound",
            expected_params=get_parameter_request("/test/invalid"),
        )

        with stubber as stub:
            var.resolve(context=runway_context)
            assert var.value == value
            stub.assert_no_pending_responses()

    def test_different_region(self, runway_context):
        """Test Lookup in region other than that set in Context."""
        name = "/test/param"
        value = "test value"
        stubber = runway_context.add_stubber("ssm", region="us-west-2")
        var = Variable(
            "test_var", "${ssm %s::region=us-west-2}" % name, variable_type="runway"
        )

        stubber.add_response(
            "get_parameter",
            get_parameter_response(name, value),
            get_parameter_request(name),
        )

        with stubber as stub:
            var.resolve(context=runway_context)
            assert var.value == value
            stub.assert_no_pending_responses()

    def test_loaded_value(self, runway_context):
        """Test resolution of a JSON value."""
        name = "/test/param"
        raw_value = {
            "nested": {"bool": True, "nest_key": "nested_val"},
            "test_key": "test_val",
        }
        stubber = runway_context.add_stubber("ssm")
        parsers = ["json", "yaml"]
        tests = [
            {"lookup": "${{ssm {name}::load={parser}}}", "expected": raw_value},
            {
                "lookup": "${{ssm {name}::load={parser},transform=str,indent=2}}",
                "expected": json.dumps(json.dumps(raw_value, indent=2)),
            },
            {
                "lookup": "${{ssm {name}::load={parser},get=nested}}",
                "expected": raw_value["nested"],
            },
            {
                "lookup": "${{ssm {name}::load={parser},get=nested.bool,transform=str}}",
                "expected": json.dumps("True"),
            },
        ]

        for parser in parsers:
            for test in tests:
                var = Variable(
                    "test_var.{}".format(parser),
                    test["lookup"].format(name=name, parser=parser),
                    variable_type="runway",
                )
                if parser == "json":
                    dumped_value = json.dumps(raw_value)
                elif parser == "yaml":
                    dumped_value = yaml.dump(raw_value)
                else:
                    raise ValueError

                stubber.add_response(
                    "get_parameter",
                    get_parameter_response(name, dumped_value),
                    get_parameter_request(name),
                )

                with stubber as stub:
                    var.resolve(context=runway_context)
                    assert var.value == test["expected"]
                    stub.assert_no_pending_responses()

    def test_not_found(self, runway_context):
        """Test raises ParameterNotFound."""
        name = "/test/param"
        stubber = runway_context.add_stubber("ssm")
        var = Variable("test_var", "${ssm %s}" % name, variable_type="runway")

        stubber.add_client_error(
            "get_parameter",
            "ParameterNotFound",
            expected_params=get_parameter_request(name),
        )

        with stubber as stub, pytest.raises(FailedVariableLookup) as err:
            var.resolve(context=runway_context)

        assert "ParameterNotFound" in str(err.value)
        stub.assert_no_pending_responses()
