"""Tests for runway.cfngin.blueprints.raw."""
# pylint: disable=unused-argument
import json
import unittest
from pathlib import Path

from mock import MagicMock

from runway.cfngin.blueprints.raw import (
    RawTemplateBlueprint,
    get_template_params,
    get_template_path,
)
from runway.util import change_dir
from runway.variables import Variable

from ..factories import mock_context

RAW_JSON_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.json")
RAW_YAML_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.yaml")
RAW_J2_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.json.j2")


def test_get_template_path_local_file(tmp_path):
    """Verify get_template_path finding a file relative to CWD."""
    template_path = Path("cfn_template.json")
    (tmp_path / "cfn_template.json").touch()

    with change_dir(tmp_path):
        result = get_template_path(template_path)
        assert template_path.samefile(result)


def test_get_template_path_invalid_file(cd_tmp_path):
    """Verify get_template_path with an invalid filename."""
    assert get_template_path(Path("cfn_template.json")) is None


def test_get_template_path_file_in_syspath(tmp_path, monkeypatch):
    """Verify get_template_path with a file in sys.path.

    This ensures templates are able to be retrieved from remote packages.

    """
    template_path = tmp_path / "cfn_template.json"
    template_path.touch()

    monkeypatch.syspath_prepend(tmp_path)
    result = get_template_path(Path(template_path.name))
    assert template_path.samefile(result)


def test_get_template_params():
    """Verify get_template_params function operation."""
    template_dict = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "TestTemplate",
        "Parameters": {
            "Param1": {"Type": "String"},
            "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
        },
        "Resources": {},
    }
    template_params = {
        "Param1": {"Type": "String"},
        "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
    }

    assert get_template_params(template_dict) == template_params


class TestBlueprintRendering(unittest.TestCase):
    """Test class for blueprint rendering."""

    def test_to_json(self):
        """Verify to_json method operation."""
        expected_json = json.dumps(
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "TestTemplate",
                "Parameters": {
                    "Param1": {"Type": "String"},
                    "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
                },
                "Resources": {
                    "Dummy": {"Type": "AWS::CloudFormation::WaitConditionHandle"}
                },
                "Outputs": {"DummyId": {"Value": "dummy-1234"}},
            },
            sort_keys=True,
            indent=4,
        )
        self.assertEqual(
            RawTemplateBlueprint(
                name="test",
                context=mock_context(),
                raw_template_path=RAW_JSON_TEMPLATE_PATH,
            ).to_json(),
            expected_json,
        )

    def test_j2_to_json(self):
        """Verify jinja2 template parsing."""
        expected_json = json.dumps(
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "TestTemplate",
                "Parameters": {
                    "Param1": {"Type": "String"},
                    "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
                },
                "Resources": {
                    "Dummy": {"Type": "AWS::CloudFormation::WaitConditionHandle"}
                },
                "Outputs": {"DummyId": {"Value": "dummy-bar-param1val-foo-1234"}},
            },
            sort_keys=True,
            indent=4,
        )
        blueprint = RawTemplateBlueprint(
            name="stack1",
            context=mock_context(
                extra_config_args={
                    "stacks": [
                        {
                            "name": "stack1",
                            "template_path": "unused",
                            "variables": {"Param1": "param1val", "bar": "foo"},
                        }
                    ]
                },
                environment={"foo": "bar"},
            ),
            raw_template_path=RAW_J2_TEMPLATE_PATH,
        )
        blueprint.resolve_variables(
            [
                Variable("Param1", "param1val", "cfngin"),
                Variable("bar", "foo", "cfngin"),
            ]
        )
        self.assertEqual(expected_json, blueprint.to_json())


class TestVariables(unittest.TestCase):
    """Test class for blueprint variable methods."""

    def test_get_parameter_definitions_json(self):
        """Verify get_parameter_definitions method with json raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_JSON_TEMPLATE_PATH
        )
        parameters = blueprint.get_parameter_definitions()
        self.assertEqual(
            parameters,
            {
                "Param1": {"Type": "String"},
                "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
            },
        )

    def test_get_parameter_definitions_yaml(self):
        """Verify get_parameter_definitions method with yaml raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_YAML_TEMPLATE_PATH
        )
        parameters = blueprint.get_parameter_definitions()
        self.assertEqual(
            parameters,
            {
                "Param1": {"Type": "String"},
                "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
            },
        )

    def test_get_required_parameter_definitions_json(self,):
        """Verify get_required_param... method with json raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_JSON_TEMPLATE_PATH
        )
        self.assertEqual(
            blueprint.get_required_parameter_definitions(),
            {"Param1": {"Type": "String"}},
        )

    def test_get_required_parameter_definitions_yaml(self,):
        """Verify get_required_param... method with yaml raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_YAML_TEMPLATE_PATH
        )
        self.assertEqual(
            blueprint.get_required_parameter_definitions(),
            {"Param1": {"Type": "String"}},
        )
