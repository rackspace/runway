"""CFNgin package source models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Extra, root_validator

from ..base import ConfigProperty


class GitCfnginPackageSourceDefinitionModel(ConfigProperty):
    """Model for a git package source definition.

    Package source located in a git repo.

    Attributes:
        branch: Branch name.
        commit: Commit hash.
        configs: List of CFNgin config paths to execute.
        paths: List of paths to append to ``sys.path``.
        tag: Git tag.
        uri: Remote git repo URI.

    """

    branch: Optional[str] = None
    commit: Optional[str] = None
    configs: List[str] = []  # TODO try Path
    paths: List[str] = []  # TODO try Path
    tag: Optional[str] = None
    uri: str  # TODO try a Url type

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid

    @root_validator
    def _validate_one_ref(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N805
        """Ensure that only one ref is defined."""
        ref_keys = ["branch", "commit", "tag"]
        count_ref_defs = sum(1 for i in ref_keys if values.get(i))
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

    configs: List[str] = []  # TODO try Path
    paths: List[str] = []  # TODO try Path
    source: str  # TODO try Path

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


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

    bucket: str
    configs: List[str] = []  # TODO try Path
    key: str
    paths: List[str] = []  # TODO try Path
    requester_pays: bool = False
    use_latest: bool = False

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


class CfnginPackageSourcesDefinitionModel(ConfigProperty):
    """Model for a CFNgin package sources definition.

    Attributes:
        git: Package source located in a git repo.
        local: Package source located on a local disk.
        s3: Package source located in AWS S3.

    """

    git: List[GitCfnginPackageSourceDefinitionModel] = []
    local: List[LocalCfnginPackageSourceDefinitionModel] = []
    s3: List[S3CfnginPackageSourceDefinitionModel] = []

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid
