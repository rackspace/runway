"""Test runway.lookups.handlers.ssm."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from runway.exceptions import FailedVariableLookup
from runway.variables import Variable

if TYPE_CHECKING:
    from ...factories import MockCfnginContext, MockRunwayContext


def get_parameter_response(
    name: str,
    value: str,
    *,
    value_type: str = "String",
    label: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Generate a mock ssm.get_parameter response."""
    selector = f"{name}/{label or version}"
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


def get_parameter_request(name: str, decrypt: bool = True) -> dict[str, bool | str]:
    """Generate the expected request parameters for ssm.get_parameter."""
    return {"Name": name, "WithDecryption": decrypt}


class TestSsmLookup:
    """Test runway.lookups.handlers.ssm.SsmLookup."""

    def test_handle_basic(
        self, cfngin_context: MockCfnginContext, runway_context: MockRunwayContext
    ) -> None:
        """Test resolution of a basic lookup."""
        name = "/test/param"
        value = "test value"
        cfngin_stubber = cfngin_context.add_stubber("ssm")
        runway_stubber = runway_context.add_stubber("ssm")
        cfngin_var = Variable("test_var", f"${{ssm {name}}}", variable_type="cfngin")
        runway_var = Variable("test_var", f"${{ssm {name}}}", variable_type="runway")

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

    @pytest.mark.parametrize("default_value", ["foo", ""])
    def test_handle_default(self, default_value: str, runway_context: MockRunwayContext) -> None:
        """Test resolution of a default value."""
        stubber = runway_context.add_stubber("ssm")
        var = Variable(
            "test_var",
            f"${{ssm /test/invalid::default={default_value}}}",
            variable_type="runway",
        )

        stubber.add_client_error(
            "get_parameter",
            "ParameterNotFound",
            expected_params=get_parameter_request("/test/invalid"),
        )

        with stubber:
            var.resolve(context=runway_context)
            assert var.value == default_value
        stubber.assert_no_pending_responses()

    def test_handle_default_nested(self, runway_context: MockRunwayContext) -> None:
        """Test resolution of a default value."""
        name = "/test/param"
        value = "test value"
        stubber = runway_context.add_stubber("ssm")
        var = Variable(
            "test_var",
            f"${{ssm /test/invalid::load=json, default=${{ssm {name}}}}}",
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

    def test_handle_different_region(self, runway_context: MockRunwayContext) -> None:
        """Test Lookup in region other than that set in Context."""
        name = "/test/param"
        value = "test value"
        stubber = runway_context.add_stubber("ssm", region="us-west-2")
        var = Variable("test_var", f"${{ssm {name}::region=us-west-2}}", variable_type="runway")

        stubber.add_response(
            "get_parameter",
            get_parameter_response(name, value),
            get_parameter_request(name),
        )

        with stubber as stub:
            var.resolve(context=runway_context)
            assert var.value == value
            stub.assert_no_pending_responses()

    def test_handle_loaded_value(self, runway_context: MockRunwayContext) -> None:
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
                    f"test_var.{parser}",
                    test["lookup"].format(name=name, parser=parser),  # type: ignore
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

    def test_handle_not_found(self, runway_context: MockRunwayContext) -> None:
        """Test raises ParameterNotFound."""
        name = "/test/param"
        stubber = runway_context.add_stubber("ssm")
        var = Variable("test_var", f"${{ssm {name}}}", variable_type="runway")

        stubber.add_client_error(
            "get_parameter",
            "ParameterNotFound",
            expected_params=get_parameter_request(name),
        )

        with stubber as stub, pytest.raises(FailedVariableLookup) as err:
            var.resolve(context=runway_context)

        assert "ParameterNotFound" in str(err.value.__cause__)
        stub.assert_no_pending_responses()

    def test_handle_no_value(self, runway_context: MockRunwayContext) -> None:
        """Test handle no ``Value`` in response."""
        name = "/test/param"
        value = "foo"
        stubber = runway_context.add_stubber("ssm")
        var = Variable("test_var", f"${{ssm {name}}}", variable_type="runway")
        response = get_parameter_response(name, value)
        response["Parameter"].pop("Value", None)
        stubber.add_response("get_parameter", response, get_parameter_request(name))

        with stubber:
            var.resolve(context=runway_context)
            assert var.value is None
        stubber.assert_no_pending_responses()

    def test_handle_string_list(self, runway_context: MockRunwayContext) -> None:
        """Test handle ``StringList`` returned as list."""
        name = "/test/param"
        value = ["foo", "bar"]
        stubber = runway_context.add_stubber("ssm")
        var = Variable("test_var", f"${{ssm {name}}}", variable_type="runway")
        stubber.add_response(
            "get_parameter",
            get_parameter_response(name, ",".join(value), value_type="StringList"),
            get_parameter_request(name),
        )

        with stubber:
            var.resolve(context=runway_context)
            assert var.value == value
        stubber.assert_no_pending_responses()
