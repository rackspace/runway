"""Tests for runway.cfngin.blueprints.raw."""

# pyright: basic
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from mock import MagicMock, Mock

from runway.cfngin.blueprints.raw import (
    RawTemplateBlueprint,
    get_template_path,
    resolve_variable,
)
from runway.cfngin.exceptions import (
    UnresolvedBlueprintVariable,
    UnresolvedBlueprintVariables,
)
from runway.utils import change_dir
from runway.variables import Variable

from ..factories import mock_context

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext

MODULE = "runway.cfngin.blueprints.raw"

RAW_JSON_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.json")
RAW_YAML_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.yaml")
RAW_J2_TEMPLATE_PATH = Path("tests/unit/cfngin/fixtures/cfn_template.json.j2")


class TestRawTemplateBlueprint:
    """Test RawTemplateBlueprint."""

    def test_get_output_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test get_output_definitions."""
        mock_output_definitions = mocker.patch.object(
            RawTemplateBlueprint, "output_definitions", "success"
        )
        assert (
            RawTemplateBlueprint(
                name="test", context=cfngin_context, raw_template_path=tmp_path
            ).get_output_definitions()
            == mock_output_definitions
        )

    def test_get_parameter_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test get_parameter_definitions."""
        mock_parameter_definitions = mocker.patch.object(
            RawTemplateBlueprint, "parameter_definitions", "success"
        )
        assert (
            RawTemplateBlueprint(
                name="test", context=cfngin_context, raw_template_path=tmp_path
            ).get_parameter_definitions()
            == mock_parameter_definitions
        )

    def test_get_parameter_values(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test get_parameter_values."""
        mock_parameter_values = mocker.patch.object(
            RawTemplateBlueprint, "parameter_values", "success"
        )
        assert (
            RawTemplateBlueprint(
                name="test", context=cfngin_context, raw_template_path=tmp_path
            ).get_parameter_values()
            == mock_parameter_values
        )

    def test_output_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test output_definitions."""
        mock_to_dict = mocker.patch.object(
            RawTemplateBlueprint,
            "to_dict",
            return_value={"Outputs": {"Test": {"Value": "test"}}},
        )
        assert (
            RawTemplateBlueprint(
                "test", cfngin_context, raw_template_path=tmp_path
            ).output_definitions
            == mock_to_dict.return_value["Outputs"]
        )
        mock_to_dict.assert_called_once_with()

    def test_parameter_definitions(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test parameter_definitions."""
        mock_to_dict = mocker.patch.object(
            RawTemplateBlueprint,
            "to_dict",
            return_value={"Parameters": {"Test": {"Type": "String"}}},
        )
        assert (
            RawTemplateBlueprint(
                "test", cfngin_context, raw_template_path=tmp_path
            ).parameter_definitions
            == mock_to_dict.return_value["Parameters"]
        )
        mock_to_dict.assert_called_once_with()

    def test_parameter_definitions_json(self) -> None:
        """Verify parameter_definitions method with json raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_JSON_TEMPLATE_PATH
        )
        assert blueprint.parameter_definitions == {
            "Param1": {"Type": "String"},
            "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
        }

    def test_parameter_definitions_yaml(self) -> None:
        """Verify parameter_definitions method with yaml raw template."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_YAML_TEMPLATE_PATH
        )
        assert blueprint.parameter_definitions == {
            "Param1": {"Type": "String"},
            "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
        }

    def test_parameter_values(self, cfngin_context: CfnginContext, tmp_path: Path) -> None:
        """Test parameter_values."""
        obj = RawTemplateBlueprint("test", cfngin_context, raw_template_path=tmp_path)
        assert not obj.parameter_values and isinstance(obj.parameter_values, dict)
        obj._resolved_variables = {"var": "val"}
        del obj.parameter_values
        assert obj.parameter_values == {"var": "val"}

    def test_required_parameter_definitions_json(self) -> None:
        """Verify required_parameter_definitions."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_JSON_TEMPLATE_PATH
        )
        assert blueprint.required_parameter_definitions == {"Param1": {"Type": "String"}}

    def test_required_parameter_definitions_yaml(self) -> None:
        """Verify required_parameter_definitions."""
        blueprint = RawTemplateBlueprint(
            name="test", context=MagicMock(), raw_template_path=RAW_YAML_TEMPLATE_PATH
        )
        assert blueprint.required_parameter_definitions == {"Param1": {"Type": "String"}}

    def test_requires_change_set(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test requires_change_set."""
        mock_to_dict = mocker.patch.object(
            RawTemplateBlueprint,
            "to_dict",
            side_effect=[{"Transform": "something"}, {}],
        )
        assert RawTemplateBlueprint(
            "test", cfngin_context, raw_template_path=tmp_path
        ).requires_change_set
        mock_to_dict.assert_called_once_with()
        assert not RawTemplateBlueprint(
            "test", cfngin_context, raw_template_path=tmp_path
        ).requires_change_set

    def test_to_dict(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test to_dict."""
        mock_parse_cloudformation_template = mocker.patch(
            f"{MODULE}.parse_cloudformation_template", return_value="success"
        )
        mock_rendered = mocker.patch.object(RawTemplateBlueprint, "rendered", "rendered template")
        assert (
            RawTemplateBlueprint("test", cfngin_context, raw_template_path=tmp_path).to_dict()
            == mock_parse_cloudformation_template.return_value
        )
        mock_parse_cloudformation_template.assert_called_once_with(mock_rendered)

    def test_to_json(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test to_json."""
        mock_to_dict = mocker.patch.object(RawTemplateBlueprint, "to_dict", return_value="dict")
        mock_dumps = Mock(return_value="success")
        mocker.patch(f"{MODULE}.json", dumps=mock_dumps)
        assert (
            RawTemplateBlueprint("test", cfngin_context, raw_template_path=tmp_path).to_json()
            == mock_dumps.return_value
        )
        mock_to_dict.assert_called_once_with()
        mock_dumps.assert_called_once_with(mock_to_dict.return_value, sort_keys=True, indent=4)

    def test_to_json_cfn_template(self, cfngin_context: CfnginContext) -> None:
        """Test to_json."""
        expected_json = json.dumps(
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "TestTemplate",
                "Parameters": {
                    "Param1": {"Type": "String"},
                    "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
                },
                "Resources": {"Dummy": {"Type": "AWS::CloudFormation::WaitConditionHandle"}},
                "Outputs": {"DummyId": {"Value": "dummy-1234"}},
            },
            sort_keys=True,
            indent=4,
        )
        assert (
            RawTemplateBlueprint(
                name="test",
                context=cfngin_context,
                raw_template_path=RAW_JSON_TEMPLATE_PATH,
            ).to_json()
            == expected_json
        )

    def test_to_json_j2(self) -> None:
        """Test to_json jinja2 template parsing."""
        expected_json = json.dumps(
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "TestTemplate",
                "Parameters": {
                    "Param1": {"Type": "String"},
                    "Param2": {"Default": "default", "Type": "CommaDelimitedList"},
                },
                "Resources": {"Dummy": {"Type": "AWS::CloudFormation::WaitConditionHandle"}},
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
                parameters={"foo": "bar"},
            ),
            raw_template_path=RAW_J2_TEMPLATE_PATH,
        )
        blueprint.resolve_variables(
            [
                Variable("Param1", "param1val", "cfngin"),
                Variable("bar", "foo", "cfngin"),
            ]
        )
        assert expected_json == blueprint.to_json()

    def test_render_template(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test render_template."""
        mock_rendered = mocker.patch.object(RawTemplateBlueprint, "rendered", "rendered")
        mock_version = mocker.patch.object(RawTemplateBlueprint, "version", "version")
        assert RawTemplateBlueprint(
            "test", cfngin_context, raw_template_path=tmp_path
        ).render_template() == (mock_version, mock_rendered)

    def test_variables(self, cfngin_context: CfnginContext, tmp_path: Path) -> None:
        """Test variables."""
        obj = RawTemplateBlueprint("test", cfngin_context, raw_template_path=tmp_path)
        with pytest.raises(UnresolvedBlueprintVariables):
            _ = obj.variables
        # obj.resolve_variables([Variable("Var0", "test")])
        obj._resolved_variables = {"var": "val"}
        assert obj.variables == {"var": "val"}
        obj.variables = {"key": "val"}
        assert obj.variables == {"key": "val"}

    def test_version(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test version."""
        mocker.patch.object(RawTemplateBlueprint, "rendered", "success")
        assert (
            RawTemplateBlueprint("test", cfngin_context, raw_template_path=tmp_path).version
            == "260ca9dd"
        )


def test_get_template_path_local_file(tmp_path: Path) -> None:
    """Verify get_template_path finding a file relative to CWD."""
    template_path = Path("cfn_template.json")
    (tmp_path / "cfn_template.json").touch()

    with change_dir(tmp_path):
        result = get_template_path(template_path)
        assert template_path.samefile(cast(Path, result))


def test_get_template_path_invalid_file(cd_tmp_path: Path) -> None:
    """Verify get_template_path with an invalid filename."""
    assert get_template_path(Path("cfn_template.json")) is None


def test_get_template_path_file_in_syspath(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Verify get_template_path with a file in sys.path.

    This ensures templates are able to be retrieved from remote packages.

    """
    template_path = tmp_path / "cfn_template.json"
    template_path.touch()

    monkeypatch.syspath_prepend(tmp_path)
    result = get_template_path(Path(template_path.name))
    assert template_path.samefile(cast(Path, result))


def test_resolve_variable() -> None:
    """Test resolve_variable."""
    assert resolve_variable(Variable("var", "val", variable_type="cfngin"), "test") == "val"


def test_resolve_variable_raise_unresolved() -> None:
    """Test resolve_variable."""
    with pytest.raises(UnresolvedBlueprintVariable):
        resolve_variable(Variable("var", "${cfn val}", variable_type="cfngin"), "test")
