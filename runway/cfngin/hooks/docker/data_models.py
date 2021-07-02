"""Hook data models.

These are makeshift data models for use until Runway v2 is realeased and pydantic
can be used.

"""
from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    ItemsView,
    List,
    NoReturn,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import Literal

from ....core.providers.aws import AccountDetails
from ....utils import MutableMap

if TYPE_CHECKING:
    from docker.models.images import Image

    from ....context import CfnginContext

    Model = TypeVar("Model", bound="BaseModel")


ECR_REPO_FQN_TEMPLATE = (
    "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo_name}"
)


class BaseModel:
    """Base model."""

    def __init__(
        self, *, context: Optional[CfnginContext] = None, **_kwargs: Any
    ) -> None:
        """Instantiate class."""
        self._ctx = context

    def dict(self) -> Dict[str, Any]:
        """Return object as a dict."""
        return {k: v for k, v in self.__iter__() if not k.startswith("_")}

    def find(self, query: str, default: Any = None, **kwargs: Any) -> Any:
        """Find a value in the object."""
        split_query = query.split(".")

        if len(split_query) == 1:
            return self.get(split_query[0], default, **kwargs)

        nested_value = self.get(split_query[0])

        if not nested_value:
            if self.get(query):
                return self.get(query)
            return default

        try:
            nested_value = nested_value.find(
                query=".".join(split_query[1:]), default=default, **kwargs
            )
            return nested_value
        except (AttributeError, KeyError):
            return default

    def get(self, name: str, default: Any = None) -> Any:
        """Get a value or return default if it is not found.

        Attr:
            name: The value to look for.
            default: Returned if no other value is found.

        """
        return getattr(self, name, default)

    @staticmethod
    def _validate_bool(value: Any) -> bool:
        """Validate a bool type attribute."""
        if isinstance(value, bool):
            return value
        return bool(value)

    @overload
    @classmethod
    def _validate_dict(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @overload
    @classmethod
    def _validate_dict(cls, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        ...

    @overload
    @classmethod
    def _validate_dict(
        cls, value: Optional[Dict[str, Any]], optional: Literal[True]
    ) -> Optional[Dict[str, Any]]:
        ...

    @overload
    @classmethod
    def _validate_dict(
        cls, value: Dict[str, Any], optional: bool = ..., required: bool = ...
    ) -> Dict[str, str]:
        ...

    @overload
    @classmethod
    def _validate_dict(
        cls, value: None, optional: bool = ..., required: Literal[True] = ...
    ) -> NoReturn:
        ...

    @overload
    @classmethod
    def _validate_dict(
        cls, value: Literal[None], optional: Literal[True], required: Literal[False]
    ) -> None:
        ...

    @classmethod
    def _validate_dict(
        cls,
        value: Optional[Union[Dict[str, Any], Any]],
        optional: bool = False,
        required: bool = False,
    ) -> Optional[Union[Dict[str, Any], NoReturn]]:
        """Validate a Dict type attribute."""
        if not value:
            if required:
                raise ValueError("Dict can't be empty or NoneType")
            if not isinstance(value, dict):
                if optional:
                    return None
                return {}
        if isinstance(value, dict):
            return value
        return cls._validate_dict(dict(value), optional=optional, required=required)

    @classmethod
    def _validate_int(
        cls, value: Any, optional: bool = False, required: bool = False
    ) -> Optional[int]:
        """Validate int type attribute."""
        if not value and value != 0:
            if required:
                raise ValueError("int can't be NoneType")
            if optional:
                return None
        if isinstance(value, int):
            return value
        return cls._validate_int(int(value or 0), optional=optional, required=required)

    @classmethod
    def _validate_list_str(
        cls,
        value: Union[List[str], Any],
        optional: bool = False,
        required: bool = False,
    ) -> Optional[List[str]]:
        """Validate a List[str] type attribute."""
        if not value:
            if required:
                raise ValueError("List can't be empty or NoneType")
            if not isinstance(value, list):
                if optional:
                    return None
                return []
        if isinstance(value, list):
            if all(isinstance(i, str) for i in value):
                return value
            for i in value:
                if not isinstance(i, str):
                    raise TypeError(f"expected List[str] not List[{type(i).__name__}]")
        return cls._validate_list_str(  # type: ignore
            list(value), optional=optional, required=required
        )

    @staticmethod
    def _validate_path(value: Any, must_exist: bool = False) -> Path:
        """Validate a Path type attribute.

        Args:
            value: A Path object or string that can be converted into a Path object.
            must_exist: Raise an error if the path provided does not exist.

        """
        if isinstance(value, str):
            value = Path(value)
        if not isinstance(value, Path):
            raise TypeError(f"expected Union[Path, str] not {type(value).__name__}")
        if must_exist and not value.exists():
            raise ValueError(f"provided path does not exist: {value.resolve()}")
        return value

    @classmethod
    def _validate_str(
        cls, value: Any, optional: bool = False, required: bool = False
    ) -> Optional[str]:
        """Validate str type attribute."""
        if not value:
            if required:
                raise ValueError("value can't be empty or NoneType")
            if not isinstance(value, str) and optional:
                return None
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, set, tuple)):
            raise TypeError(f"value can't be {type(value).__name__}")  # type: ignore
        return cls._validate_str(str(value), optional=optional, required=required)

    @classmethod
    def parse_obj(
        cls: Type[Model], obj: Any, context: Optional[CfnginContext] = None
    ) -> Model:
        """Parse object."""
        if not isinstance(obj, dict):
            try:
                obj = dict(obj)
            except (TypeError, ValueError):
                raise TypeError(
                    f"{cls.__name__} expected dict not {obj.__class__.__name__}"
                ) from None
        return cls(context=context, **obj)

    def __eq__(self, other: Any) -> bool:
        """Evaluate equal comparison operator."""
        if isinstance(other, self.__class__):
            return self.dict() == other.dict()
        return self.dict() == other

    def __getitem__(self, name: str) -> bool:
        """Implement evaluation of self[name].

        Args:
            name: The value to look for.

        Raises:
            KeyError: Object does not contain a field of the name provided.

        """
        return getattr(self, name)

    def __iter__(self) -> ItemsView[str, Any]:
        """Iterate object."""
        yield from self.__dict__.items()

    def __setitem__(self, name: str, value: Any) -> None:
        """Implement assignment to self[key].

        Args:
            name: Attribute name to associate with a value.
            value: Value of a key/attribute.

        """
        setattr(self, name, value)


class ElasticContainerRegistry(BaseModel):
    """AWS Elastic Container Registry.

    Attributes:
        account_id: AWS account ID that owns the registry being logged into.
        alias: If it is a public repository, the alias of the repository.
        public: Whether the repository is public.
        region: AWS region where the registry is located.

    """

    PUBLIC_URI_TEMPLATE: ClassVar[str] = "public.ecr.aws/{registry_alias}/"
    URI_TEMPLATE: ClassVar[str] = "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/"

    account_id: Optional[str]
    alias: Optional[str]
    region: Optional[str]
    public: bool

    def __init__(
        self,
        *,
        account_id: Optional[str] = None,
        alias: Optional[str] = None,
        aws_region: Optional[str] = None,
        context: Optional[CfnginContext] = None,
        **kwargs: Any,
    ) -> None:
        """Instantiate class."""
        super().__init__(context=context, **kwargs)
        self.account_id = self._validate_str(account_id, optional=True)
        self.alias = self._validate_str(alias, optional=True)
        self.region = self._validate_str(aws_region, optional=True)
        self.public = bool(self.alias)

        if not self.public:
            if not self._ctx and not (self.account_id or self.region):
                raise ValueError("context is required to resolve values")
            if not self.region:
                self.region = self._validate_str(
                    self._ctx.env.aws_region if self._ctx else "us-east-1",
                    required=True,
                )
            if not self.account_id:
                self.account_id = AccountDetails(cast("CfnginContext", self._ctx)).id

    @property
    def fqn(self) -> str:
        """Fully qualified ECR name."""
        if self.public:
            return self.PUBLIC_URI_TEMPLATE.format(registry_alias=self.alias)
        return self.URI_TEMPLATE.format(
            aws_account_id=self.account_id, aws_region=self.region
        )


class DockerImage(BaseModel):
    """Wrapper for :class:`docker.models.images.Image`."""

    _repo: Optional[str]
    image: Image

    def __init__(self, *, image: Image, **kwargs: Any) -> None:
        """Instantiate class."""
        super().__init__(**kwargs)
        self._repo = None
        self.image = image

    @property
    def id(self) -> str:
        """ID of the image."""
        return cast(str, self.image.id)

    @id.setter
    def id(self, value: str) -> None:
        """Set the ID of the image."""
        self.image.id = value  # type: ignore

    @property
    def repo(self) -> str:
        """Repository URI."""
        if not self._repo:
            self._repo = self.image.attrs["RepoTags"][0].rsplit(":", 1)[0]
        return cast(str, self._repo)

    @repo.setter
    def repo(self, value: str) -> None:
        """Set repository URI value."""
        self._repo = value

    @property
    def short_id(self) -> str:
        """ID of the image truncated to 10 characters plus the ``sha256:`` prefix."""
        return cast(str, self.image.short_id)

    @short_id.setter
    def short_id(self, value: str) -> None:
        """Set the ID of the image truncated to 10 characters plus the ``sha256:`` prefix."""
        self.image.short_id = value  # type: ignore

    @property
    def tags(self) -> List[str]:
        """List of image tags."""
        self.image.reload()
        return [uri.split(":")[-1] for uri in cast(List[str], self.image.tags)]

    @property
    def uri(self) -> MutableMap:
        """Return a mapping of tag to image URI."""
        return MutableMap(
            **{uri.split(":")[-1]: uri for uri in cast(List[str], self.image.tags)}
        )


class ElasticContainerRegistryRepository(BaseModel):
    """AWS Elastic Container Registry (ECR) Repository.

    Attributes:
        name: The name of the repository.
        registry: Information about an ECR registry.

    """

    name: str
    registry: ElasticContainerRegistry

    def __init__(
        self,
        *,
        account_id: Optional[str] = None,
        aws_region: Optional[str] = None,
        context: Optional[CfnginContext] = None,
        registry_alias: Optional[str] = None,
        repo_name: str,
        **kwargs: Any,
    ) -> None:
        """Instantiace class.

        Args:
            account_id: AWS account ID.
            aws_region: AWS region.
            context: CFNgin context object.
            registry_alias: Alias of a public ECR registry.
            repo_name: Name of the ECR repository.

        """
        super().__init__(context=context, **kwargs)
        self.name = cast(str, self._validate_str(repo_name, required=True))

        self.registry = ElasticContainerRegistry(
            account_id=account_id,
            alias=registry_alias,
            aws_region=aws_region,
            context=context,
        )

    @property
    def fqn(self) -> str:
        """Fully qualified ECR repo name."""
        return self.registry.fqn + self.name
