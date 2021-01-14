"""Hook data models.

These are makeshift data models for use until Runway v2 is realeased and pydantic
can be used.

"""
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

from ....core.providers.aws import AccountDetails
from ....util import MutableMap

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # type: ignore pylint: disable=E

if TYPE_CHECKING:
    from docker.models.images import Image

    from ...context import Context

    # TODO remove pylint disable when dropping python 2 support
    Model = TypeVar("Model", bound="BaseModel")  # pylint: disable=invalid-name


ECR_REPO_FQN_TEMPLATE = (
    "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{repo_name}"
)


class BaseModel(object):
    """Base model."""

    def dict(self):  # type: () -> Dict[str, Any]
        """Return object as a dict."""
        return {k: v for k, v in self.__iter__() if not k.startswith("_")}

    def find(self, query, default=None, **kwargs):  # type: (str, Any, Any) -> Any
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

    def get(self, name, default=None):  # type: (str, Any) -> Any
        """Get a value or return default if it is not found.

        Attr:
            name: The value to look for.
            default: Returned if no other value is found.

        """
        return getattr(self, name, default)

    @staticmethod
    def _validate_bool(value):
        # type: (Any) -> bool
        """Validate a bool type attribute."""
        if isinstance(value, bool):
            return value
        return bool(value)

    @classmethod
    def _validate_dict(cls, value, optional=False, required=False):
        # type: (Any, bool, bool) -> Dict[str, Any]
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
    def _validate_int(cls, value, optional=False, required=False):
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
    def _validate_list_str(cls, value, optional=False, required=False):
        # type: (Any, bool, bool) -> List[str]
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
                    raise TypeError(
                        "expected List[str] not List[{}]".format(type(i).__name__)
                    )
        return cls._validate_list_str(list(value), required=required)

    @staticmethod
    def _validate_path(value, must_exist=False):
        # type: (Any, bool) -> Path
        """Validate a Path type attribute.

        Args:
            value: A Path object or string that can be converted into a Path object.
            must_exist: Raise an error if the path provided does not exist.

        """
        if isinstance(value, str):
            value = Path(value)
        if not isinstance(value, Path):
            raise TypeError(
                "expected Union[Path, str] not {}".format(type(value).__name__)
            )
        if must_exist and not value.exists():
            raise ValueError(
                "provided path does not exist: {}".format(str(value.resolve()))
            )
        return value

    @classmethod
    def _validate_str(cls, value, optional=False, required=False):
        # type: (Any, bool, bool) -> Optional[str]
        """Validate str type attribute."""
        if not value:
            if required:
                raise ValueError("value can't be empty or NoneType")
            if not isinstance(value, str) and optional:
                return None
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, set, tuple)):
            raise TypeError("value can't be {}".format(type(value).__name__))
        return cls._validate_str(str(value), optional=optional, required=required)

    @classmethod
    def parse_obj(
        cls,  # type: Type["Model"]
        obj,  # type: Any
        context=None,  # type: Optional["Context"]
    ):
        # type: (...) -> "Model"
        """Parse object."""
        if not isinstance(obj, dict):
            try:
                obj = dict(obj)
            except (TypeError, ValueError):
                raise TypeError(
                    "{} expected dict not {}".format(
                        cls.__name__, obj.__class__.__name__
                    )
                )
        return cls(context=context, **obj)

    def __eq__(self, other):
        # type: (Any) -> bool
        """Evaluate equal comparison operator."""
        if isinstance(other, self.__class__):
            return self.dict() == other.dict()
        return self.dict() == other

    def __getitem__(self, name):  # type: (str) -> Any
        """Implement evaluation of self[name].

        Args:
            name: The value to look for.

        Raises:
            KeyError: Object does not contain a field of the name provided.

        """
        return getattr(self, name)

    def __iter__(self):  # type: () -> Generator[Tuple[str, Any], None, None]
        """Iterate object."""
        # yield from self.__dict__.items()  # TODO replace with this when dropping python 2
        for k, v in self.__dict__.items():
            yield k, v

    def __ne__(self, other):  # TODO remove when dropping python 2 support
        # type: (Any) -> bool
        """Override the default implementation (unnecessary in Python 3)."""
        return not self.__eq__(other)  # cov: ignore

    def __setitem__(self, name, value):
        # type: (str, Any) -> None
        """Implement assignment to self[key].

        Args:
            name: Attribute name to associate with a value.
            value: Value of a key/attribute.

        """
        setattr(self, name, value)


class ElasticContainerRegistry(BaseModel):
    """AWS Elastic Container Registry."""

    PUBLIC_URI_TEMPLATE = "public.ecr.aws/{registry_alias}/"
    URI_TEMPLATE = "{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/"

    def __init__(
        self,
        account_id=None,  # type: Optional[str]
        alias=None,  # type: Optional[str]
        aws_region=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):  # type: (...) -> None
        """Instantiate class."""
        self._ctx = kwargs.get("context")  # type: Optional["Context"]
        self.account_id = self._validate_str(account_id, optional=True)
        self.alias = self._validate_str(alias, optional=True)
        self.region = self._validate_str(aws_region, optional=True)
        self.public = bool(self.alias)

        if not self.public:
            if not self._ctx and not (self.account_id or self.region):
                raise ValueError("context is required to resolve values")
            if not self.region:
                self.region = self._validate_str(
                    self._ctx.region or "us-east-1", required=True
                )
            if not self.account_id:
                self.account_id = AccountDetails(self._ctx).id

    @property
    def fqn(self):  # type: () -> str
        """Fully qualified ECR name."""
        if self.public:
            return self.PUBLIC_URI_TEMPLATE.format(registry_alias=self.alias)
        return self.URI_TEMPLATE.format(
            aws_account_id=self.account_id, aws_region=self.region
        )


class DockerImage(BaseModel):
    """Wrapper for :class:`docker.models.images.Image`."""

    def __init__(self, image):  # type: (Image) -> None
        """Instantiate class."""
        self._repo = None  # caching
        self.image = image

    @property
    def id(self):  # type: () -> str
        """ID of the image."""
        return self.image.id

    @id.setter
    def id(self, value):  # type: (str) -> None
        """Set the ID of the image."""
        self.image.id = value

    @property
    def repo(self):  # type: () -> str
        """Repository URI."""
        if not self._repo:
            self._repo = self.image.attrs["RepoTags"][0].rsplit(":", 1)[0]
        return self._repo

    @repo.setter
    def repo(self, value):  # type: (str) -> None
        """Set repository URI value."""
        self._repo = value

    @property
    def short_id(self):  # type: () -> str
        """ID of the image truncated to 10 characters plus the ``sha256:`` prefix."""
        return self.image.short_id

    @short_id.setter
    def short_id(self, value):  # type: (str) -> None
        """Set the ID of the image truncated to 10 characters plus the ``sha256:`` prefix."""
        self.image.short_id = value

    @property
    def tags(self):  # type: () -> List[str]
        """List of image tags."""
        self.image.reload()
        return [uri.split(":")[-1] for uri in self.image.tags]

    @property
    def uri(self):  # type: () -> MutableMap
        """Return a mapping of tag to image URI."""
        return MutableMap(**{uri.split(":")[-1]: uri for uri in self.image.tags})


class ElasticContainerRegistryRepository(BaseModel):
    """AWS Elastic Container Registry (ECR) Repository."""

    def __init__(
        self,
        repo_name,  # type: str
        account_id=None,  # type: Optional[str]
        aws_region=None,  # type: Optional[str]
        registry_alias=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):  # type: (...) -> None
        """Instantiace class.

        Args:
            account_id: AWS account ID.
            aws_region: AWS region.
            registry_alias: Alias of a public ECR registry.
            repo_name: Name of the ECR repository.

        """
        self.name = self._validate_str(repo_name, required=True)

        self.registry = ElasticContainerRegistry(
            account_id=account_id,
            alias=registry_alias,
            aws_region=aws_region,
            context=kwargs.get("context"),
        )

    @property
    def fqn(self):  # type: () -> str
        """Fully qualified ECR repo name."""
        return self.registry.fqn + self.name
