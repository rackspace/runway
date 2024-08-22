"""Runway static site Module options."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from pydantic import ConfigDict, model_validator

from ....config.models.base import ConfigProperty


class RunwayStaticSiteExtraFileDataModel(ConfigProperty):
    """Model for Runway static site Module extra_files option item."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module extra_files option item",
        validate_assignment=True,
        validate_default=True,
    )

    content_type: str | None = None
    """An explicit content type for the file.
    If not provided, will attempt to determine based on the name provided.

    """

    content: Any = None
    """Inline content that will be used as the file content.
    This or ``file`` must be provided.

    """

    file: Path | None = None
    """Path to an existing file.
    The content of this file will be uploaded to the static site S3 bucket using
    the name as the object key.
    This or ``content`` must be provided.

    """

    name: str
    """The destination name of the file to create."""

    @model_validator(mode="before")
    @classmethod
    def _autofill_content_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Attempt to fill content_type if not provided."""
        if values.get("content_type"):
            return values
        name = cast(str, values.get("name", ""))
        if name.endswith(".json"):
            values["content_type"] = "application/json"
        elif name.endswith((".yaml", ".yml")):
            values["content_type"] = "text/yaml"
        return values

    @model_validator(mode="before")
    @classmethod
    def _validate_content_or_file(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate that content or file is provided."""
        if all(i in values and values[i] for i in ["content", "file"]):
            raise ValueError("only one of content or file can be provided")
        if not any(i in values for i in ["content", "file"]):
            raise ValueError("one of content or file must be provided")
        return values


class RunwayStaticSitePreBuildStepDataModel(ConfigProperty):
    """Model for Runway static site Module pre_build_steps option item."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module pre_build_steps option item",
        validate_default=True,
        validate_assignment=True,
    )

    command: str
    """The command to run."""

    cwd: Path = Path.cwd()
    """The working directory for the subprocess running the command.
    If not provided, the current working directory is used.

    """


class RunwayStaticSiteSourceHashingDirectoryDataModel(ConfigProperty):
    """Model for Runway static site Module source_hashing.directory option item."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module source_hashing.directories option item",
        validate_default=True,
        validate_assignment=True,
    )

    exclusions: list[str] = []
    """List of gitignore formmated globs to ignore when calculating the hash."""

    path: Path
    """Path to files to include in the hash."""


class RunwayStaticSiteSourceHashingDataModel(ConfigProperty):
    """Model for Runway static site Module source_hashing option."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module source_hashing option",
        validate_default=True,
        validate_assignment=True,
    )

    directories: list[RunwayStaticSiteSourceHashingDirectoryDataModel] = [
        RunwayStaticSiteSourceHashingDirectoryDataModel(path="./")  # type: ignore
    ]
    """Explicitly provide the directories to use when calculating the hash.
    If not provided, will default to the root of the module.
    """

    enabled: bool = True
    """Enable source hashing. If not enabled, build and upload will occur on every deploy."""

    parameter: str | None = None
    """SSM parameter where the hash of each build is stored."""


class RunwayStaticSiteModuleOptionsDataModel(ConfigProperty):
    """Model for Runway static site Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway static site Module options",
        validate_default=True,
        validate_assignment=True,
    )

    build_output: str = "./"
    """Directory where build output is placed. Defaults to current working directory."""

    build_steps: list[str] = []
    """List of commands to run to build the static site."""

    extra_files: list[RunwayStaticSiteExtraFileDataModel] = []
    """List of files that should be uploaded to S3 after the build.
    Used to dynamically create or select file.
    """

    pre_build_steps: list[RunwayStaticSitePreBuildStepDataModel] = []
    """Commands to be run prior to the build process."""

    source_hashing: RunwayStaticSiteSourceHashingDataModel = (
        RunwayStaticSiteSourceHashingDataModel()
    )
    """Overrides for source hash calculation and tracking."""
