"""CFNgin config."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from string import Template
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Union,
    cast,
)

import yaml

from ..cfngin import exceptions
from ..cfngin.lookups import register_lookup_handler
from ..cfngin.utils import SourceProcessor
from ..exceptions import ConfigNotFound
from ..utils import merge_dicts
from .components.runway import (
    RunwayDeploymentDefinition,
    RunwayTestDefinition,
    RunwayVariablesDefinition,
)
from .models.cfngin import (
    CfnginConfigDefinitionModel,
    CfnginHookDefinitionModel,
    CfnginPackageSourcesDefinitionModel,
    CfnginStackDefinitionModel,
)
from .models.runway import RunwayConfigDefinitionModel, RunwayFutureDefinitionModel

if TYPE_CHECKING:
    from packaging.specifiers import SpecifierSet
    from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class BaseConfig:
    """Base class for configurations."""

    file_path: Path
    _data: BaseModel

    def __init__(self, data: BaseModel, *, path: Optional[Path] = None) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.

        """
        self._data = data.copy()
        self.file_path = path.resolve() if path else Path.cwd()

    def dump(
        self,
        *,
        by_alias: bool = False,
        exclude: Optional[
            Union[AbstractSet[Union[int, str]], Mapping[Union[int, str], Any]]
        ] = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = True,
        include: Optional[
            Union[AbstractSet[Union[int, str]], Mapping[Union[int, str], Any]]
        ] = None,
    ) -> str:
        """Dump model to a YAML string.

        Args:
            by_alias: Whether field aliases should be used as keys in the
                returned dictionary.
            exclude: Fields to exclude from the returned dictionary.
            exclude_defaults: Whether fields which are equal to their default
                values (whether set or otherwise) should be excluded from
                the returned dictionary.
            exclude_none: Whether fields which are equal to None should be
                excluded from the returned dictionary.
            exclude_unset: Whether fields which were not explicitly set when
                creating the model should be excluded from the returned
                dictionary.
            include: Fields to include in the returned dictionary.

        """
        return yaml.dump(
            self._data.dict(
                by_alias=by_alias,
                exclude=exclude,  # type: ignore
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                include=include,  # type: ignore
            ),
            default_flow_style=False,
        )

    @classmethod
    def find_config_file(cls, path: Path) -> Optional[Path]:
        """Find a config file in the provided path.

        Args:
            path: The path to search for a config file.

        """
        raise NotImplementedError  # cov: ignore


class CfnginConfig(BaseConfig):
    """Python representation of a CFNgin config file.

    This is used internally by CFNgin to parse and validate a YAML formatted
    CFNgin configuration file, but can also be used in scripts to generate a
    CFNgin config file before handing it off to CFNgin to deploy/destroy.

    Example::

        from runway.cfngin.config import dump, Config, Stack

        vpc = Stack({
            "name": "vpc",
            "class_path": "blueprints.VPC"})

        config = Config()
        config.namespace = "prod"
        config.stacks = [vpc]

        print dump(config)

    """

    EXCLUDE_REGEX = r"runway(\..*)?\.(yml|yaml)"
    EXCLUDE_LIST = ["bitbucket-pipelines.yml", "buildspec.yml", "docker-compose.yml"]

    #: Bucket to use for CFNgin resources. (e.g. CloudFormation templates).
    #: May be an empty string.
    cfngin_bucket: Optional[str]
    #: Explicit region to use for :attr:`CfnginConfig.cfngin_bucket`
    cfngin_bucket_region: Optional[str]
    """Explicit region to use for :attr:`CfnginConfig.cfngin_bucket`"""
    cfngin_cache_dir: Path  #: Local directory to use for caching.
    log_formats: Dict[str, str]  #: Custom formatting for log messages.
    lookups: Dict[str, str]  #: Register custom lookups.
    mappings: Dict[  #: Mappings that will be added to all stacks.
        str, Dict[str, Dict[str, Any]]
    ]
    namespace: str  #: Namespace to prepend to everything.
    # Character used to separate :attr:`CfnginConfig.namespace` and anything it prepends.
    namespace_delimiter: str
    package_sources: CfnginPackageSourcesDefinitionModel  #: Remote source locations.
    persistent_graph_key: Optional[  #: S3 object key were the persistent graph is stored.
        str
    ] = None
    post_deploy: List[CfnginHookDefinitionModel]  #: Hooks to run after a deploy action.
    post_destroy: List[  #: Hooks to run after a destroy action.
        CfnginHookDefinitionModel
    ]
    pre_deploy: List[CfnginHookDefinitionModel]  #: Hooks to run before a deploy action.
    pre_destroy: List[  #: Hooks to run before a destroy action.
        CfnginHookDefinitionModel
    ]
    service_role: Optional[str]  #: IAM role for CloudFormation to use.
    stacks: List[CfnginStackDefinitionModel]  #: Stacks to be processed.
    sys_path: Optional[Path]  #: Relative or absolute path to use as the work directory.
    tags: Optional[Dict[str, str]]  #: Tags to apply to all resources.
    template_indent: int  #: Spaces to use per-indent level when outputing a template to json.

    _data: CfnginConfigDefinitionModel

    def __init__(
        self, data: CfnginConfigDefinitionModel, *, path: Optional[Path] = None
    ) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.

        """
        super().__init__(data, path=path)

        self.cfngin_bucket = self._data.cfngin_bucket
        self.cfngin_bucket_region = self._data.cfngin_bucket_region
        self.cfngin_cache_dir = self._data.cfngin_cache_dir
        self.log_formats = self._data.log_formats
        self.lookups = self._data.lookups
        self.mappings = self._data.mappings
        self.namespace = self._data.namespace
        self.namespace_delimiter = self._data.namespace_delimiter
        self.package_sources = self._data.package_sources
        self.persistent_graph_key = self._data.persistent_graph_key
        self.post_deploy = cast(List[CfnginHookDefinitionModel], self._data.post_deploy)
        self.post_destroy = cast(
            List[CfnginHookDefinitionModel], self._data.post_destroy
        )
        self.pre_deploy = cast(List[CfnginHookDefinitionModel], self._data.pre_deploy)
        self.pre_destroy = cast(List[CfnginHookDefinitionModel], self._data.pre_destroy)
        self.service_role = self._data.service_role
        self.stacks = cast(List[CfnginStackDefinitionModel], self._data.stacks)
        self.sys_path = self._data.sys_path
        self.tags = self._data.tags
        self.template_indent = self._data.template_indent

    def load(self) -> None:
        """Load config options into the current environment/session."""
        if self.sys_path:
            LOGGER.debug("appending to sys.path: %s", self.sys_path)
            sys.path.append(str(self.sys_path))
            LOGGER.debug("sys.path: %s", sys.path)
        if self.lookups:
            for key, handler in self.lookups.items():
                register_lookup_handler(key, handler)

    @classmethod
    def find_config_file(  # type: ignore pylint: disable=arguments-differ
        cls, path: Optional[Path] = None, *, exclude: Optional[List[str]] = None
    ) -> List[Path]:
        """Find a config file in the provided path.

        Args:
            path: The path to search for a config file.
            exclude: List of file names to exclude. This list is appended to
                the global exclude list.

        Raises:
            ConfigNotFound: Could not find a config file in the provided path.
            ValueError: More than one config file found in the provided path.

        """
        if not path:
            path = Path.cwd()
        elif path.is_file():
            return [path]

        exclude = exclude or []
        result: List[Path] = []
        exclude.extend(cls.EXCLUDE_LIST)

        yml_files = list(path.glob("*.yml"))
        yml_files.extend(list(path.glob("*.yaml")))

        for f in yml_files:
            if (
                re.match(cls.EXCLUDE_REGEX, f.name)
                or f.name in exclude
                or f.name.startswith(".")
            ):
                continue  # cov: ignore
            result.append(f)
        result.sort()
        return result

    @classmethod
    def parse_file(  # pylint: disable=arguments-differ
        cls,
        *,
        path: Optional[Path] = None,
        file_path: Optional[Path] = None,
        parameters: Optional[MutableMapping[str, Any]] = None,
        **kwargs: Any,
    ) -> CfnginConfig:
        """Parse a YAML file to create a config object.

        Args:
            path: The path to search for a config file.
            file_path: Exact path to a file to parse.
            parameters: Values to use when resolving a raw config.

        Raises:
            ConfigNotFound: Provided config file was not found.

        """
        if file_path:
            if not file_path.is_file():
                raise ConfigNotFound(path=file_path)
            return cls.parse_raw(
                file_path.read_text(),
                path=file_path,
                parameters=parameters or {},
                **kwargs,
            )
        if path:
            found = cls.find_config_file(path)
            if len(found) > 1:
                raise ValueError(f"more than one config files found: {found}")
            return cls.parse_file(
                file_path=found[0], parameters=parameters or {}, **kwargs
            )
        raise ValueError("must provide path or file_path")

    @classmethod
    def parse_obj(cls, obj: Any, *, path: Optional[Path] = None) -> CfnginConfig:
        """Parse a python object.

        Args:
            obj: A python object to parse as a CFNgin config.
            path: The path to the config file that was parsed into the object.

        """
        return cls(CfnginConfigDefinitionModel.parse_obj(obj), path=path)

    @classmethod
    def parse_raw(
        cls,
        data: str,
        *,
        parameters: Optional[MutableMapping[str, Any]] = None,
        path: Optional[Path] = None,
        skip_package_sources: bool = False,
    ) -> CfnginConfig:
        """Parse raw data.

        Args:
            data: The raw data to parse.
            parameters: Values to use when resolving a raw config.
            path: The path to search for a config file.
            skip_package_sources: Skip processing package sources.

        """
        if not parameters:
            parameters = {}
        pre_rendered = cls.resolve_raw_data(data, parameters=parameters)
        if skip_package_sources:
            return cls.parse_obj(yaml.safe_load(pre_rendered))
        config_dict = yaml.safe_load(
            cls.process_package_sources(pre_rendered, parameters=parameters)
        )
        return cls.parse_obj(config_dict, path=path)

    @classmethod
    def process_package_sources(
        cls, raw_data: str, *, parameters: Optional[MutableMapping[str, Any]] = None
    ) -> str:
        """Process the package sources defined in a rendered config.

        Args:
            raw_data: Raw configuration data.
            parameters: Values to use when resolving a raw config.

        """
        config = yaml.safe_load(raw_data) or {}
        processor = SourceProcessor(
            sources=CfnginPackageSourcesDefinitionModel.parse_obj(
                config.get("package_sources", {})  # type: ignore
            ),
            cache_dir=config.get("cfngin_cache_dir"),
        )
        processor.get_package_sources()
        if processor.configs_to_merge:
            for i in processor.configs_to_merge:
                LOGGER.debug("merging in remote config: %s", i)
                with open(i, "rb") as opened_file:
                    config = merge_dicts(yaml.safe_load(opened_file), config)
            return cls.resolve_raw_data(yaml.dump(config), parameters=parameters or {})
        return raw_data

    @staticmethod
    def resolve_raw_data(
        raw_data: str, *, parameters: Optional[MutableMapping[str, Any]] = None
    ) -> str:
        """Resolve raw data.

        Args:
            raw_data: Raw configuration data.
            parameters: Values to use when resolving a raw config.

        Raises:
            MissingEnvironment: A value required by the config was not provided
                in parameters.

        """
        if not parameters:
            parameters = {}
        template = Template(raw_data)
        try:
            rendered = template.substitute(**parameters)
        except KeyError as err:
            raise exceptions.MissingEnvironment(err.args[0]) from None
        except ValueError:
            rendered = template.safe_substitute(**parameters)
        return rendered


class RunwayConfig(BaseConfig):
    """Python representation of a Runway config file."""

    ACCEPTED_NAMES = ["runway.yml", "runway.yaml"]

    deployments: List[RunwayDeploymentDefinition]
    file_path: Path
    future: RunwayFutureDefinitionModel
    ignore_git_branch: bool
    runway_version: Optional[SpecifierSet]
    tests: List[RunwayTestDefinition]
    variables: RunwayVariablesDefinition

    _data: RunwayConfigDefinitionModel

    def __init__(
        self, data: RunwayConfigDefinitionModel, *, path: Optional[Path] = None
    ) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.

        """
        super().__init__(data, path=path)
        self.deployments = [
            RunwayDeploymentDefinition(d) for d in self._data.deployments
        ]
        self.future = self._data.future
        self.ignore_git_branch = self._data.ignore_git_branch
        self.runway_version = self._data.runway_version
        self.tests = [RunwayTestDefinition(t) for t in self._data.tests]
        self.variables = RunwayVariablesDefinition(self._data.variables)

    @classmethod
    def find_config_file(cls, path: Path) -> Path:
        """Find a config file in the provided path.

        Args:
            path: The path to search for a config file.

        Raises:
            ConfigNotFound: Could not find a config file in the provided path.
            ValueError: More than one config file found in the provided path.

        """
        match = list(path.glob("runway.y*"))
        if not match or all(f.name not in cls.ACCEPTED_NAMES for f in match):
            match = list(path.parent.glob("runway.y*"))
        found = [f for f in match if f.is_file() and f.name in cls.ACCEPTED_NAMES]
        if not found:
            raise ConfigNotFound(looking_for=cls.ACCEPTED_NAMES, path=path)
        if len(found) != 1:
            raise ValueError(f"more than one config files found: {found}")
        return found[0]

    @classmethod
    def parse_file(
        cls,
        *,
        path: Optional[Path] = None,
        file_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> RunwayConfig:
        """Parse a YAML file to create a config object.

        Args:
            path: The path to search for a config file.
            file_path: Exact path to a file to parse.

        Raises:
            ConfigNotFound: Provided config file was not found.
            ValueError: path and file_path were both excluded.

        """
        if file_path:
            if not file_path.is_file():
                raise ConfigNotFound(path=file_path)
            return cls.parse_obj(
                yaml.safe_load(file_path.read_text()), path=file_path, **kwargs
            )
        if path:
            return cls.parse_file(file_path=cls.find_config_file(path), **kwargs)
        raise ValueError("must provide path or file_path")

    @classmethod
    def parse_obj(cls, obj: Any, *, path: Optional[Path] = None) -> RunwayConfig:
        """Parse a python object into a config object.

        Args:
            obj: The object to be parsed.
            path: Path to the file the object was parsed from.

        """
        return cls(RunwayConfigDefinitionModel.parse_obj(obj), path=path)
