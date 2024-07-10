"""Test runway.config.models.runway._builtin_tests."""

# pyright: basic
from typing import Optional

import pytest
from pydantic import ValidationError

from runway.config.models.runway import (
    CfnLintRunwayTestArgs,
    CfnLintRunwayTestDefinitionModel,
    RunwayTestDefinitionModel,
    ScriptRunwayTestArgs,
    ScriptRunwayTestDefinitionModel,
    YamlLintRunwayTestDefinitionModel,
)


class TestRunwayTestDefinitionModel:
    """Test runway.config.models.runway._builtin_tests.RunwayTestDefinitionModel."""

    def test_init_cfnlint(self) -> None:
        """Test init cfn-lint subclass."""
        data = {"type": "cfn-lint"}
        obj = RunwayTestDefinitionModel.parse_obj(data)

        assert isinstance(obj, CfnLintRunwayTestDefinitionModel)
        assert obj.args.dict() == {"cli_args": []}
        assert obj.name == "cfn-lint"
        assert obj.type == "cfn-lint"

    def test_init_script(self) -> None:
        """Test init script subclass."""
        data = {"type": "script"}
        obj = RunwayTestDefinitionModel.parse_obj(data)

        assert isinstance(obj, ScriptRunwayTestDefinitionModel)
        assert obj.args.dict() == {"commands": []}
        assert obj.name == "script"
        assert obj.type == "script"

    def test_init_yamllint(self) -> None:
        """Test init yamllint subclass."""
        data = {"type": "yamllint"}
        obj = RunwayTestDefinitionModel.parse_obj(data)

        assert isinstance(obj, YamlLintRunwayTestDefinitionModel)
        assert obj.args == {}
        assert obj.name == "yamllint"
        assert obj.type == "yamllint"

    def test_invalid_type(self) -> None:
        """Test invalid type."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayTestDefinitionModel.parse_obj({"type": "invalid"})
        assert excinfo.value.errors()[0]["loc"] == ("type",)

    @pytest.mark.parametrize("required", [None, True, False])
    def test_required(self, required: Optional[bool]) -> None:
        """Test required."""
        if isinstance(required, bool):
            obj = RunwayTestDefinitionModel(type="script", required=required)
            assert obj.required is required
        else:
            obj = RunwayTestDefinitionModel(type="script")
            assert obj.required is False

    def test_string_args(self) -> None:
        """Test args defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayTestDefinitionModel.parse_obj({"args": "something", "type": "yamllint"})
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("args",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_string_args_lookup(self) -> None:
        """Test args defined as a lookup string."""
        data = {"args": "${var something}", "type": "yamllint"}
        obj = RunwayTestDefinitionModel.parse_obj(data)
        assert obj.args == data["args"]

    def test_string_required(self) -> None:
        """Test required defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayTestDefinitionModel.parse_obj({"required": "something", "type": "yamllint"})
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("required",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_string_required_lookup(self) -> None:
        """Test required defined as a lookup string."""
        data = {"required": "${var something}", "type": "yamllint"}
        obj = RunwayTestDefinitionModel.parse_obj(data)
        assert obj.required == data["required"]


class TestCfnLintRunwayTestArgs:
    """Test runway.config.models.runway._builtin_tests.CfnLintRunwayTestArgs."""

    def test_cli_args_string(self) -> None:
        """Test cli_args defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            CfnLintRunwayTestArgs(cli_args="something")
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("cli_args",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_cli_args_string_lookup(self) -> None:
        """Test args defined as a lookup string."""
        data = {"cli_args": "${var something}"}
        assert CfnLintRunwayTestArgs.parse_obj(data).cli_args == data["cli_args"]

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            CfnLintRunwayTestArgs.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"


class TestCfnLintRunwayTestDefinitionModel:
    """Test runway.config.models.runway._builtin_tests.CfnLintRunwayTestDefinitionModel."""

    def test_args(self) -> None:
        """Test args."""
        data = {"args": {"cli_args": ["example"]}, "type": "cfn-lint"}
        obj = CfnLintRunwayTestDefinitionModel.parse_obj(data)
        assert isinstance(obj.args, CfnLintRunwayTestArgs)
        assert obj.args.cli_args == data["args"]["cli_args"]  # type: ignore


class TestScriptRunwayTestArgs:
    """Test runway.config.models.runway._builtin_tests.ScriptRunwayTestArgs."""

    def test_commands_string(self) -> None:
        """Test commands defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            ScriptRunwayTestArgs(commands="something")
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("commands",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_commands_string_lookup(self) -> None:
        """Test args defined as a lookup string."""
        data = {"commands": "${var something}"}
        assert ScriptRunwayTestArgs.parse_obj(data).commands == data["commands"]

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            ScriptRunwayTestArgs.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"


class TestScriptRunwayTestDefinitionModel:
    """Test runway.config.models.runway._builtin_tests.ScriptRunwayTestDefinitionModel."""

    def test_args(self) -> None:
        """Test args."""
        data = {"args": {"commands": ["example"]}}
        obj = ScriptRunwayTestDefinitionModel.parse_obj(data)
        assert isinstance(obj.args, ScriptRunwayTestArgs)
        assert obj.args.commands == data["args"]["commands"]
