"""CFNgin package source models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Extra, Field, root_validator

from ..base import ConfigProperty


class GitCfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a git package source definition.

    Package source located in a git repository.

    Attributes:
        branch: Branch name.
        commit: Commit hash.
        configs: List of CFNgin config paths to execute.
        paths: List of paths to append to ``sys.path``.
        tag: Git tag.
        uri: Remote git repo URI.

    """

    branch: Optional[str] = Field(
        None, title="Git Branch", examples=["ENV-dev", "ENV-prod", "master"]
    )
    commit: Optional[str] = Field(None, title="Git Commit Hash")
    configs: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source "
        "for configuration that should be merged into the current configuration file.",
    )
    paths: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source to add to $PATH.",
    )
    tag: Optional[str] = Field(None, title="Git Tag", examples=["1.0.0", "v1.0.0"])
    uri: str = Field(
        ...,
        title="Git Repository URI",
        examples=["git@github.com:onicagroup/runway.git"],
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Information about git repositories that should be included "
            "in the processing of this configuration file."
        }
        title = "CFNgin Git Repository Package Source Definition"

    @root_validator
    def _validate_one_ref(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure that only one ref is defined."""
        ref_keys = ["branch", "commit", "tag"]
        count_ref_defs = sum(bool(values.get(i)) for i in ref_keys)
        if count_ref_defs > 1:
            raise ValueError(f"only one of {ref_keys} can be defined")
        return values


class LocalCfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a CFNgin local package source definition.

    Package source located on a local disk.

    Attributes:
        configs: List of CFNgin config paths to execute.
        paths: List of paths to append to ``sys.path``.
        source: Source.

    """

    configs: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source "
        "for configuration that should be merged into the current configuration file.",
    )
    paths: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source to add to $PATH.",
    )
    source: str = Field(
        ...,
        description="Path relative to the current configuration file that is the "
        "root of the local package source.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Information about local directories that should be "
            "included in the processing of this configuration file."
        }
        title = "CFNgin Local Package Source Definition"


class S3CfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a CFNgin S3 package source definition.

    Package source located in AWS S3.

    Attributes:
        bucket: AWS S3 bucket name.
        configs: List of CFNgin config paths to execute.
        key: Object key. The object should be a zip file.
        paths: List of paths to append to ``sys.path``.
        requester_pays: AWS S3 requester pays option.
        use_latest: Use the latest version of the object.

    """

    bucket: str = Field(..., title="AWS S3 Bucket Name")
    configs: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source "
        "for configuration that should be merged into the current configuration file.",
    )
    key: str = Field(..., title="AWS S3 Object Key")
    paths: List[str] = Field(
        [],
        description="Array of paths relative to the root of the package source to add to $PATH.",
    )
    requester_pays: bool = Field(
        False,
        description="Confirms that the requester knows that they will be charged "
        "for the request.",
    )
    use_latest: bool = Field(
        True,
        description="Update the local copy if the last modified date in AWS S3 changes.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Information about a AWS S3 objects that should be "
            "downloaded, unzipped, and included in the processing of "
            "this configuration file."
        }
        title = "CFNgin S3 Package Source Definition"


class CfnginPackageSourcesDefinitionModel(ConfigProperty):
    """Model for a CFNgin package sources definition.

    Attributes:
        git: Package source located in a git repo.
        local: Package source located on a local disk.
        s3: Package source located in AWS S3.

    """

    git: List[GitCfnginPackageSourceDefinitionModel] = Field(
        [],
        title="CFNgin Git Repository Package Source Definitions",
        description=GitCfnginPackageSourceDefinitionModel.Config.schema_extra[
            "description"
        ],
    )
    local: List[LocalCfnginPackageSourceDefinitionModel] = Field(
        [],
        title="CFNgin Local Package Source Definitions",
        description=LocalCfnginPackageSourceDefinitionModel.Config.schema_extra[
            "description"
        ],
    )
    s3: List[S3CfnginPackageSourceDefinitionModel] = Field(
        [],
        title="CFNgin S3 Package Source Definitions",
        description=S3CfnginPackageSourceDefinitionModel.Config.schema_extra[
            "description"
        ],
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Map of additional package sources to include when "
            "processing this configuration file."
        }
        title = "CFNgin Package Sources Definition"
