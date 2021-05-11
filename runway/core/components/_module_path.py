"""Handler for the ``path`` field of a Runway module."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Dict, Optional, Type, Union
from urllib.parse import parse_qs

from typing_extensions import TypedDict

from ...compat import cached_property
from ...config.components.runway import RunwayModuleDefinition
from ...config.models.runway import RunwayModuleDefinitionModel
from ...constants import DEFAULT_CACHE_DIR
from ...sources.git import Git
from ._deploy_environment import DeployEnvironment

if TYPE_CHECKING:
    from ...sources.source import Source

LOGGER = logging.getLogger(__name__)


class ModulePathMetadataTypeDef(TypedDict):
    """Type definition for ModulePath.metadata."""

    arguments: Dict[str, str]
    cache_dir: Path
    location: str
    source: str
    uri: str


class ModulePath:
    """Handler for the ``path`` field of a Runway module."""

    ARGS_REGEX: ClassVar[str] = r"(\?)(?P<args>.*)$"
    REMOTE_SOURCE_HANDLERS: ClassVar[Dict[str, Type[Source]]] = {"git": Git}
    SOURCE_REGEX: ClassVar[str] = r"(?P<source>[a-z]+)(\:\:)"
    URI_REGEX: ClassVar[str] = r"(?P<uri>[a-z]+://[a-zA-Z0-9\./]+?(?=//|\?|$))"

    def __init__(
        self,
        definition: Optional[Union[Path, str]] = None,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        deploy_environment: Optional[DeployEnvironment] = None,
    ) -> None:
        """Instantiate class.

        Args:
            definition: Path definition.
            cache_dir: Directory to use for caching if needed.
            deploy_environment: Current deploy environment object.

        """
        self.cache_dir = cache_dir
        self.definition = definition or Path.cwd()
        self.env = deploy_environment or DeployEnvironment()

    @cached_property
    def arguments(self) -> Dict[str, str]:
        """Remote source arguments."""
        if isinstance(self.definition, str):
            match = re.match(fr"^.*{self.ARGS_REGEX}", self.definition)
            if match:
                return {
                    k: ",".join(v) for k, v in parse_qs(match.group("args")).items()
                }
        return {}

    @cached_property
    def location(self) -> str:
        """Location of the module."""
        if isinstance(self.definition, str):
            if (
                re.match(r"^(/|//|\.|\./)", self.definition)
                or "::" not in self.definition
            ):
                return re.sub(self.ARGS_REGEX, "", self.definition)
            no_src = re.sub(fr"^{self.SOURCE_REGEX}", "", self.definition)
            no_uri = re.sub(fr"^{self.URI_REGEX}", "", no_src)
            match = re.search(r"//(?P<location>[^\?\n]*)", no_uri)
            if match:
                return match.group("location")
        return "./"

    @cached_property
    def metadata(self) -> ModulePathMetadataTypeDef:
        """Information that describes the module path."""
        return {
            "arguments": self.arguments,
            "cache_dir": self.cache_dir,
            "location": self.location,
            "source": self.source,
            "uri": self.uri,
        }

    @cached_property
    def module_root(self) -> Path:
        """Root directory of the module."""
        if isinstance(self.definition, Path):
            return self.definition
        if self.source != "local":
            return self._fetch_remote_source()
        return self.env.root_dir / self.location

    @cached_property
    def source(self) -> str:
        """Source of the module."""
        if isinstance(self.definition, str):
            match = re.match(fr"^{self.SOURCE_REGEX}.*$", self.definition)
            if match:
                return match.group("source")
        return "local"

    @cached_property
    def uri(self) -> str:
        """Remote source URI."""
        if isinstance(self.definition, str):
            match = re.match(fr"^{self.SOURCE_REGEX}{self.URI_REGEX}", self.definition)
            if match:
                return match.group("uri")
        return ""

    def _fetch_remote_source(self) -> Path:
        """Fetch remote module source.

        Raises:
            NotImplementedError: The supplied source does not have a handler.

        """
        try:
            return self.REMOTE_SOURCE_HANDLERS[self.source](**self.metadata).fetch()
        except KeyError:
            raise NotImplementedError(
                f"{self.source} is not a supported Runway module source"
            ) from None

    @classmethod
    def parse_obj(
        cls,
        obj: Optional[
            Union[Path, RunwayModuleDefinition, RunwayModuleDefinitionModel, str]
        ],
        *,
        deploy_environment: Optional[DeployEnvironment] = None,
    ) -> ModulePath:
        """Parse object.

        Args:
            obj: Object to parse.
            deploy_environment: Current deploy environment object.

        Raises:
            TypeError: Unsupported type provided.

        """
        if isinstance(obj, (RunwayModuleDefinition, RunwayModuleDefinitionModel)):
            return cls(definition=obj.path, deploy_environment=deploy_environment)
        if isinstance(obj, (type(None), Path, str)):
            return cls(definition=obj, deploy_environment=deploy_environment)
        raise TypeError(
            f"object type {type(obj)}; expected pathlib.Path, "
            "RunwayModuleDefinition, RunwayModuleDefinitionModel, or str"
        )
