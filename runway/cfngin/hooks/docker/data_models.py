"""Hook data models.

These are makeshift data models for use until Runway v2 is realeased and pydantic
can be used.

"""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, cast

from docker.models.images import Image
from pydantic import Field, root_validator

from ....core.providers.aws import AccountDetails
from ....utils import BaseModel, MutableMap

if TYPE_CHECKING:
    from ....context import CfnginContext


ECR_REPO_FQN_TEMPLATE = (
    "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo_name}"
)


class ElasticContainerRegistry(BaseModel):
    """AWS Elastic Container Registry."""

    PUBLIC_URI_TEMPLATE: ClassVar[str] = "public.ecr.aws/{registry_alias}/"
    URI_TEMPLATE: ClassVar[str] = "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/"

    _ctx: Optional[CfnginContext] = Field(default=None, alias="context", exclude=True)
    """CFNgin context."""

    account_id: Optional[str] = None
    """AWS account ID that owns the registry being logged into."""

    alias: Optional[str] = None
    """If it is a public repository, the alias of the repository."""

    public: bool = True
    """Whether the repository is public."""

    region: Optional[str] = Field(default=None, alias="aws_region")
    """AWS region where the registry is located."""

    @property
    def fqn(self) -> str:
        """Fully qualified ECR name."""
        if self.public:
            return self.PUBLIC_URI_TEMPLATE.format(registry_alias=self.alias)
        return self.URI_TEMPLATE.format(
            aws_account_id=self.account_id, aws_region=self.region
        )

    @root_validator(allow_reuse=True, pre=True)
    def _set_defaults(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Set default values based on other values."""
        values.setdefault("public", bool(values.get("alias")))

        if not values["public"]:
            account_id = values.get("account_id")
            ctx: Optional[CfnginContext] = values.get("context")
            region = values.get("aws_region")
            if not ctx and not (account_id or region):
                raise ValueError("context is required to resolve values")
            if ctx:
                if not account_id:
                    values["account_id"] = AccountDetails(ctx).id
                if not region:
                    values["aws_region"] = ctx.env.aws_region or "us-east-1"

        return values


class DockerImage(BaseModel):
    """Wrapper for :class:`docker.models.images.Image`."""

    image: Image
    _repo: Optional[str] = None

    class Config:
        """Model configuration."""

        arbitrary_types_allowed = True
        fields = {"_repo": {"exclude": True}}
        underscore_attrs_are_private = True

    @property
    def id(self) -> str:
        """ID of the image."""
        return self.image.id

    @property
    def repo(self) -> str:
        """Repository URI."""
        if not self._repo:
            self._repo = self.image.attrs["RepoTags"][0].rsplit(":", 1)[0]
        return cast(str, self._repo)

    @property
    def short_id(self) -> str:
        """ID of the image truncated to 10 characters plus the ``sha256:`` prefix."""
        return self.image.short_id

    @property
    def tags(self) -> List[str]:
        """List of image tags."""
        self.image.reload()
        return [uri.split(":")[-1] for uri in self.image.tags]

    @property
    def uri(self) -> MutableMap:
        """Return a mapping of tag to image URI."""
        return MutableMap(**{uri.split(":")[-1]: uri for uri in self.image.tags})


class ElasticContainerRegistryRepository(BaseModel):
    """AWS Elastic Container Registry (ECR) Repository."""

    name: str = Field(..., alias="repo_name")
    """The name of the repository."""

    registry: ElasticContainerRegistry
    """Information about an ECR registry."""

    @property
    def fqn(self) -> str:
        """Fully qualified ECR repo name."""
        return self.registry.fqn + self.name
