"""Test runway.config.components.runway._test_def."""

# pylint: disable=protected-access
# pyright: basic
import pytest
from pydantic import ValidationError

from runway.config.components.runway import (
    CfnLintRunwayTestDefinition,
    RunwayTestDefinition,
    ScriptRunwayTestDefinition,
    YamlLintRunwayTestDefinition,
)
from runway.config.models.runway import (
    CfnLintRunwayTestDefinitionModel,
    ScriptRunwayTestDefinitionModel,
    YamlLintRunwayTestDefinitionModel,
)


class TestCfnLintRunwayTestDefinition:
    """Test runway.config.components.runway._test_def.CfnLintRunwayTestDefinition."""

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        assert isinstance(
            CfnLintRunwayTestDefinition.parse_obj({}), CfnLintRunwayTestDefinition
        )


class TestRunwayTestDefinition:
    """Test runway.config.components.runway._test_def.RunwayTestDefinition."""

    def test_new_cfn_lint(self) -> None:
        """Test creation CfnLintRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition(CfnLintRunwayTestDefinitionModel()),
            CfnLintRunwayTestDefinition,
        )

    def test_new_invalid(self) -> None:
        """Test new invalid type."""
        with pytest.raises(TypeError) as excinfo:
            RunwayTestDefinition({})  # type: ignore
        assert str(excinfo.value).startswith("expected data of type")

    def test_new_script(self) -> None:
        """Test creation ScriptRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition(ScriptRunwayTestDefinitionModel()),
            ScriptRunwayTestDefinition,
        )

    def test_new_yamllint(self) -> None:
        """Test creation ScriptRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition(YamlLintRunwayTestDefinitionModel()),
            YamlLintRunwayTestDefinition,
        )

    def test_parse_obj_cfn_lint(self) -> None:
        """Test parse_obj CfnLintRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition.parse_obj({"type": "cfn-lint"}),
            CfnLintRunwayTestDefinition,
        )

    def test_parse_obj_invalid(self) -> None:
        """Test parse_obj invalid object."""
        with pytest.raises(ValidationError):
            RunwayTestDefinition.parse_obj({"type": "invalid"})

    def test_parse_obj_script(self) -> None:
        """Test parse_obj ScriptRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition.parse_obj({"type": "script"}),
            ScriptRunwayTestDefinition,
        )

    def test_parse_obj_yamllint(self) -> None:
        """Test parse_obj YamlLintRunwayTestDefinition."""
        assert isinstance(
            RunwayTestDefinition.parse_obj({"type": "yamllint"}),
            YamlLintRunwayTestDefinition,
        )

    def test_register_variable(self) -> None:
        """Test _register_variable."""
        obj = RunwayTestDefinition.parse_obj(
            {"type": "script", "name": "test_register_variable", "required": True}
        )
        assert obj._vars["required"].name == "test_register_variable.required"


class TestScriptRunwayTestDefinition:
    """Test runway.config.components.runway._test_def.ScriptRunwayTestDefinition."""

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        assert isinstance(
            ScriptRunwayTestDefinition.parse_obj({}), ScriptRunwayTestDefinition
        )


class TestYamlLintRunwayTestDefinition:
    """Test runway.config.components.runway._test_def.YamlLintRunwayTestDefinition."""

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        assert isinstance(
            YamlLintRunwayTestDefinition.parse_obj({}), YamlLintRunwayTestDefinition
        )
