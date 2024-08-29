"""CFNgin package source models."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import ConfigDict, Field, model_validator

from ..base import ConfigProperty


class GitCfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a git package source definition.

    Package source located in a git repository.

    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Information about git repositories that should be included "
            "in the processing of this configuration file."
        },
        title="CFNgin Git Repository Package Source Definition",
        validate_default=True,
        validate_assignment=True,
    )

    branch: Annotated[
        str | None, Field(title="Git Branch", examples=["ENV-dev", "ENV-prod", "master"])
    ] = None
    """Branch name."""

    commit: Annotated[str | None, Field(title="Git Commit Hash")] = None
    """Commit hash."""

    configs: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source "
            "for configuration that should be merged into the current configuration file."
        ),
    ] = []
    """List of CFNgin config paths to execute."""

    paths: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source to add to $PATH."
        ),
    ] = []
    """List of paths to append to ``sys.path``."""

    tag: Annotated[str | None, Field(title="Git Tag", examples=["1.0.0", "v1.0.0"])] = None
    """Git tag."""

    uri: Annotated[
        str, Field(title="Git Repository URI", examples=["git@github.com:rackspace/runway.git"])
    ]
    """Remote git repo URI."""

    @model_validator(mode="before")
    @classmethod
    def _validate_one_ref(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure that only one ref is defined."""
        ref_keys = ["branch", "commit", "tag"]
        count_ref_defs = sum(bool(values.get(i)) for i in ref_keys)
        if count_ref_defs > 1:
            raise ValueError(f"only one of {ref_keys} can be defined")
        return values


class LocalCfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a CFNgin local package source definition.

    Package source located on a local disk.

    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Information about local directories that should be "
            "included in the processing of this configuration file."
        },
        title="CFNgin Local Package Source Definition",
        validate_default=True,
        validate_assignment=True,
    )

    configs: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source "
            "for configuration that should be merged into the current configuration file.",
        ),
    ] = []
    """List of CFNgin config paths to execute."""

    paths: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source to add to $PATH."
        ),
    ] = []
    """List of paths to append to ``sys.path``."""

    source: Annotated[
        str,
        Field(
            description="Path relative to the current configuration file that is the "
            "root of the local package source."
        ),
    ]
    """Source."""


class S3CfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a CFNgin S3 package source definition.

    Package source located in AWS S3.

    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Information about a AWS S3 objects that should be "
            "downloaded, unzipped, and included in the processing of "
            "this configuration file."
        },
        title="CFNgin S3 Package Source Definition",
        validate_default=True,
        validate_assignment=True,
    )

    bucket: Annotated[str, Field(title="AWS S3 Bucket Name")]
    """AWS S3 bucket name."""

    configs: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source "
            "for configuration that should be merged into the current configuration file.",
        ),
    ] = []
    """List of CFNgin config paths to execute."""

    key: Annotated[str, Field(title="AWS S3 Object Key")]
    """Object key. The object should be a zip file."""

    paths: Annotated[
        list[str],
        Field(
            description="Array of paths relative to the root of the package source to add to $PATH."
        ),
    ] = []
    """List of paths to append to ``sys.path``."""

    requester_pays: Annotated[
        bool,
        Field(
            description="Confirms that the requester knows that they will be charged for the request."
        ),
    ] = False
    """AWS S3 requester pays option."""

    use_latest: Annotated[
        bool,
        Field(description="Update the local copy if the last modified date in AWS S3 changes."),
    ] = True
    """Use the latest version of the object."""


class CfnginPackageSourcesDefinitionModel(ConfigProperty):
    """Model for a CFNgin package sources definition."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Map of additional package sources to include when "
            "processing this configuration file."
        },
        title="CFNgin Package Sources Definition",
        validate_default=True,
        validate_assignment=True,
    )

    git: list[GitCfnginPackageSourceDefinitionModel] = Field(
        default=[],
        title="CFNgin Git Repository Package Source Definitions",
        description="Information about git repositories that should be included "
        "in the processing of this configuration file.",
    )
    """Package source located in a git repo."""

    local: list[LocalCfnginPackageSourceDefinitionModel] = Field(
        default=[],
        title="CFNgin Local Package Source Definitions",
        description="Information about local directories that should be included "
        "in the processing of this configuration file.",
    )
    """Package source located on a local disk."""

    s3: list[S3CfnginPackageSourceDefinitionModel] = Field(
        default=[],
        title="CFNgin S3 Package Source Definitions",
        description="Information about a AWS S3 objects that should be "
        "downloaded, unzipped, and included in the processing of this configuration file.",
    )
    """Package source located in AWS S3."""
