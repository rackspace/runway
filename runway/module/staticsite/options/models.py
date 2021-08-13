"""Runway static site Module options."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from pydantic import Extra, root_validator

from ....config.models.base import ConfigProperty


class RunwayStaticSiteExtraFileDataModel(ConfigProperty):
    """Model for Runway static site Module extra_files option item.

    Attributes:
        content_type: An explicit content type for the file. If not provided,
            will attempt to determine based on the name provided.
        content: Inline content that will be used as the file content.
            This or ``file`` must be provided.
        file: Path to an existing file. The content of this file will be uploaded
            to the static site S3 bucket using the name as the object key.
            This or ``content`` must be provided.
        name: The destination name of the file to create.

    """

    content_type: Optional[str]
    content: Any = None
    file: Optional[Path]
    name: str

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module extra_files option item."

    @root_validator
    def _autofill_content_type(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to fill content_type if not provided."""
        if values.get("content_type"):
            return values
        name = cast(str, values.get("name", ""))
        if name.endswith(".json"):
            values["content_type"] = "application/json"
        elif name.endswith(".yaml") or name.endswith(".yml"):
            values["content_type"] = "text/yaml"
        return values

    @root_validator(pre=True)
    def _validate_content_or_file(  # pylint: disable=no-self-argument,no-self-use
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that content or file is provided."""
        content = values.get("content")
        file_val = values.get("file")
        if content and file_val:
            raise ValueError("only one of content or file can be provided")
        if not (content or file_val):
            raise ValueError("one of content or file must be provided")
        return values


class RunwayStaticSitePreBuildStepDataModel(ConfigProperty):
    """Model for Runway static site Module pre_build_steps option item.

    Attributes:
        command: The command to run.
        cwd: The working directory for the subprocess running the command.
            If not provided, the current working directory is used.

    """

    command: str
    cwd: Path = Path.cwd()

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module pre_build_steps option item."


class RunwayStaticSiteSourceHashingDirectoryDataModel(ConfigProperty):
    """Model for Runway static site Module source_hashing.directory option item.

    Attributes:
        exclusions: List of gitignore formmated globs to ignore when calculating
            the hash.
        path: Path to files to include in the hash.

    """

    exclusions: List[str] = []
    path: Path

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module source_hashing.directories option item."


class RunwayStaticSiteSourceHashingDataModel(ConfigProperty):
    """Model for Runway static site Module source_hashing option.

    Attributes:
        directories: Explicitly provide the directories to use when calculating
            the hash. If not provided, will default to the root of the module.
        enabled: Enable source hashing. If not enabled, build and upload will
            occur on every deploy.
        parameter: SSM parameter where the hash of each build is stored.

    """

    directories: List[RunwayStaticSiteSourceHashingDirectoryDataModel] = [
        RunwayStaticSiteSourceHashingDirectoryDataModel(path="./")
    ]
    enabled: bool = True
    parameter: Optional[str] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module source_hashing option."


class RunwayStaticSiteModuleOptionsDataModel(ConfigProperty):
    """Model for Runway static site Module options.

    Attributes:
        build_output: Directory where build output is placed. Defaults to current
            working directory.
        build_steps: List of commands to run to build the static site.
        extra_files: List of files that should be uploaded to S3 after the build.
            Used to dynamically create or select file.
        pre_build_steps: Commands to be run prior to the build process.
        source_hashing: Overrides for source hash calculation and tracking.

    """

    build_output: str = "./"
    build_steps: List[str] = []
    extra_files: List[RunwayStaticSiteExtraFileDataModel] = []
    pre_build_steps: List[RunwayStaticSitePreBuildStepDataModel] = []
    source_hashing: RunwayStaticSiteSourceHashingDataModel = (
        RunwayStaticSiteSourceHashingDataModel()
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway static site Module options."
