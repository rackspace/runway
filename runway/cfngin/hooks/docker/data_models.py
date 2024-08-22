"""Hook data models.

These are makeshift data models for use until Runway v2 is released and pydantic
can be used.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar, cast

from docker.models.images import Image
from pydantic import ConfigDict, Field, PrivateAttr, model_validator

from ....core.providers.aws import AccountDetails
from ....utils import BaseModel, MutableMap

if TYPE_CHECKING:
    from ....context import CfnginContext

ECR_REPO_FQN_TEMPLATE = "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo_name}"


class ElasticContainerRegistry(BaseModel):
    """AWS Elastic Container Registry."""

    PUBLIC_URI_TEMPLATE: ClassVar[str] = "public.ecr.aws/{registry_alias}/"
    URI_TEMPLATE: ClassVar[str] = "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/"

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    account_id: str | None = None
    """AWS account ID that owns the registry being logged into."""

    alias: str | None = None
    """If it is a public repository, the alias of the repository."""

    public: bool = True
    """Whether the repository is public."""

    region: str | None = Field(default=None, alias="aws_region")
    """AWS region where the registry is located."""

    @property
    def fqn(self) -> str:
        """Fully qualified ECR name."""
        if self.public:
            return self.PUBLIC_URI_TEMPLATE.format(registry_alias=self.alias)
        return self.URI_TEMPLATE.format(aws_account_id=self.account_id, aws_region=self.region)

    @model_validator(mode="before")
    @classmethod
    def _set_defaults(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set default values based on other values."""
        values.setdefault("public", bool(values.get("alias")))

        if not values["public"]:
            account_id = values.get("account_id")
            ctx: CfnginContext | None = values.get("context")
            aws_region = values.get("aws_region")
            if not ctx and not (account_id or aws_region):
                raise ValueError("context is required to resolve values")
            if ctx:
                if not account_id:
                    values["account_id"] = AccountDetails(ctx).id
                if not aws_region:
                    values["aws_region"] = ctx.env.aws_region or "us-east-1"
        return values


class DockerImage(BaseModel):
    """Wrapper for :class:`docker.models.images.Image`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _repo: str | None = PrivateAttr(default=None)
    image: Image

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
    def tags(self) -> list[str]:
        """List of image tags."""
        self.image.reload()
        return [uri.split(":")[-1] for uri in self.image.tags]

    @property
    def uri(self) -> MutableMap:
        """Return a mapping of tag to image URI."""
        return MutableMap(**{uri.split(":")[-1]: uri for uri in self.image.tags})

    def __bool__(self) -> bool:
        """Evaluate the boolean value of the object instance."""
        return True


class ElasticContainerRegistryRepository(BaseModel):
    """AWS Elastic Container Registry (ECR) Repository."""

    model_config = ConfigDict(populate_by_name=True)

    name: Annotated[str, Field(alias="repo_name")]
    """The name of the repository."""

    registry: ElasticContainerRegistry
    """Information about an ECR registry."""

    @property
    def fqn(self) -> str:
        """Fully qualified ECR repo name."""
        return self.registry.fqn + self.name
