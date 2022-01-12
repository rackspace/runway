"""Runway test definition models."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Union, cast

from pydantic import Extra, Field, validator
from typing_extensions import Literal

from .. import utils
from ..base import ConfigProperty

if TYPE_CHECKING:
    from typing import Callable

ValidRunwayTestTypeValues = Literal["cfn-lint", "script", "yamllint"]


class RunwayTestDefinitionModel(ConfigProperty):
    """Model for a Runway test definition."""

    args: Union[Dict[str, Any], ConfigProperty, str] = Field(
        default={},
        title="Arguments",
        description="Arguments to be passed to the test. Support varies by test type.",
    )
    name: str = Field(default="test-name", description="Name of the test.")
    required: Union[bool, str] = Field(
        default=False,
        description="Whether the test must pass for subsequent tests to be run.",
    )
    type: ValidRunwayTestTypeValues

    class Config(ConfigProperty.Config):
        """Model configuration."""

        schema_extra = {
            "description": "Tests that can be run via the 'test' command.",
        }
        title = "Runway Test Definition"
        use_enum_values = True

    def __new__(cls, **kwargs: Any) -> RunwayTestDefinitionModel:
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
                return super().__new__(YamlLintRunwayTestDefinitionModel)
        return super().__new__(cls)

    # TODO add regex to schema
    _validate_string_is_lookup = cast(
        "classmethod[Callable[..., Any]]",
        validator("args", "required", allow_reuse=True, pre=True)(
            utils.validate_string_is_lookup
        ),
    )


class CfnLintRunwayTestArgs(ConfigProperty):
    """Model for the args of a cfn-lint test."""

    cli_args: Union[List[str], str] = Field(
        default=[],
        title="CLI Arguments",
        description="Array of arguments to pass to the cfn-lint CLI.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Arguments supported by the cfn-lint test.",
        }
        title = "cfn-lint Runway Test Arguments"

    # TODO add regex to schema
    _validate_string_is_lookup = cast(
        "classmethod[Callable[..., Any]]",
        validator("cli_args", allow_reuse=True, pre=True)(
            utils.validate_string_is_lookup
        ),
    )


class CfnLintRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a cfn-lint test definition."""

    args: CfnLintRunwayTestArgs = Field(
        default=CfnLintRunwayTestArgs(),
        title="Arguments",
        description="Arguments to be passed to the test.",
    )
    name: str = Field(default="cfn-lint", description="Name of the test.")
    required: Union[bool, str] = Field(
        default=False,
        description="Whether the test must pass for subsequent tests to be run.",
    )
    type: Literal["cfn-lint"] = Field(
        default="cfn-lint", description="The type of test to run."
    )

    class Config(RunwayTestDefinitionModel.Config):
        """Model configuration."""

        schema_extra = {
            "description": "Test using cfn-lint.",
        }
        title = "cfn-lint Test"


class ScriptRunwayTestArgs(ConfigProperty):
    """Model for the args of a script test."""

    commands: Union[List[str], str] = Field(
        default=[], description="Array of commands that will be run for this test."
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Arguments supported by the script test.",
        }
        title = "Script Runway Test Arguments"

    # TODO add regex to schema
    _validate_string_is_lookup = cast(
        "classmethod[Callable[..., Any]]",
        validator("commands", allow_reuse=True, pre=True)(
            utils.validate_string_is_lookup
        ),
    )


class ScriptRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a script test definition."""

    args: ScriptRunwayTestArgs = Field(
        default=ScriptRunwayTestArgs(),
        title="Arguments",
        description="Arguments to be passed to the test.",
    )
    name: str = Field(default="script", description="Name of the test.")
    required: Union[bool, str] = Field(
        default=False,
        description="Whether the test must pass for subsequent tests to be run.",
    )
    type: Literal["script"] = Field(
        default="script", description="The type of test to run."
    )

    class Config(RunwayTestDefinitionModel.Config):
        """Model configuration."""

        schema_extra = {
            "description": "Test using a custom script.",
        }
        title = "Script Test"


class YamlLintRunwayTestDefinitionModel(RunwayTestDefinitionModel):
    """Model for a yamllint test definition."""

    name: str = Field(default="yamllint", description="Name of the test.")
    required: Union[bool, str] = Field(
        default=False,
        description="Whether the test must pass for subsequent tests to be run.",
    )
    type: Literal["yamllint"] = Field(
        default="yamllint", description="The type of test to run."
    )

    class Config(RunwayTestDefinitionModel.Config):
        """Model configuration."""

        schema_extra = {
            "description": "Test using yamllint.",
        }
        title = "yamllint Test"
