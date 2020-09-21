"""Runway test definition models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Extra
from typing_extensions import Literal

from ....util import snake_case_to_kebab_case
from ..base import ConfigProperty


class ValidRunwayTestTypeValues(Enum):
    """Valid build-in test types."""

    cfn_lint = "cfn-lint"
    script = "script"
    yamllint = "yamllint"


class RunwayTestDefinitionModel(ConfigProperty):
    """Model for a Runway test definition."""

    args: Dict[str, Any] = {}
    name: Optional[str] = None
    required: bool = True
    type: ValidRunwayTestTypeValues

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        use_enum_values = True

    def __new__(cls, **kwargs) -> RunwayTestDefinitionModel:
        """Create a new instance of a class.

        Returns:
            Correct subclass of RunwayTestDefinition for the given data.

        """
        test_type = kwargs.get("type")
        if cls is RunwayTestDefinitionModel:
            if test_type == "cfn-lint":
                return super().__new__(CfnLintRunwayTestDefinitionModel)
            if test_type == "script":
                return super().__new__(ScriptRunwayTestDefinitionModel)
            if test_type == "yamllint":
                return super.__new__(YamlLintRunwayTestDefinitionModel)
        return super().__new__(cls)


class CfnLintRunwayTestArgs(ConfigProperty):
    """Model for the args of a cfn-lint test."""

    cli_args: List[str] = []

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        alias_generator = snake_case_to_kebab_case
        allow_population_by_field_name = True
        extra = Extra.forbid


class CfnLintRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a cfn-lint test definition."""

    args: CfnLintRunwayTestArgs = CfnLintRunwayTestArgs()
    name: Optional[str] = "cfn-lint"
    type: Literal["cfn-lint"]


class ScriptRunwayTestArgs(ConfigProperty):
    """Model for the args of a script test."""

    commands: List[str] = []

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


class ScriptRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a script test definition."""

    args: ScriptRunwayTestArgs = ScriptRunwayTestArgs()
    type: Literal["script"]


class YamlLintRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a yamllint test definition."""

    name: Optional[str] = "yamllint"
    type: Literal["yamllint"]
