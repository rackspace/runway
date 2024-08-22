"""CFNgin config."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

import yaml

from ..cfngin import exceptions
from ..cfngin.lookups.registry import register_lookup_handler
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
    from collections.abc import Mapping, MutableMapping

    from packaging.specifiers import SpecifierSet
    from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)

_ModelTypeVar = TypeVar("_ModelTypeVar", bound="BaseModel")


class BaseConfig(Generic[_ModelTypeVar]):
    """Base class for configurations."""

    file_path: Path
    _data: _ModelTypeVar

    def __init__(self, data: _ModelTypeVar, *, path: Path | None = None) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.

        """
        self._data = data.model_copy()
        self.file_path = path.resolve() if path else Path.cwd()

    def dump(
        self,
        *,
        by_alias: bool = False,
        exclude: set[int | str] | Mapping[int | str, Any] | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = True,
        include: set[int | str] | Mapping[int | str, Any] | None = None,
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
            self._data.model_dump(
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
    def find_config_file(cls, path: Path) -> Path | None:
        """Find a config file in the provided path.

        Args:
            path: The path to search for a config file.

        """
        raise NotImplementedError  # cov: ignore


class CfnginConfig(BaseConfig[CfnginConfigDefinitionModel]):
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
    """Regex for file names to exclude when looking for config files."""

    EXCLUDE_LIST = ["bitbucket-pipelines.yml", "buildspec.yml", "docker-compose.yml"]
    """Explicit files names to ignore when looking for config files."""

    cfngin_bucket: str | None
    """Bucket to use for CFNgin resources. (e.g. CloudFormation templates).
    May be an empty string.
    """

    cfngin_bucket_region: str | None
    """Explicit region to use for :attr:`CfnginConfig.cfngin_bucket`"""

    cfngin_cache_dir: Path
    """Local directory to use for caching."""

    log_formats: dict[str, str]
    """Custom formatting for log messages."""

    lookups: dict[str, str]
    """Register custom lookups."""

    mappings: dict[str, dict[str, dict[str, Any]]]
    """Mappings that will be added to all stacks."""

    namespace: str
    """Namespace to prepend to everything."""

    namespace_delimiter: str
    """Character used to separate :attr:`CfnginConfig.namespace` and anything it prepends."""

    package_sources: CfnginPackageSourcesDefinitionModel
    """Remote source locations."""

    persistent_graph_key: str | None = None
    """S3 object key were the persistent graph is stored."""

    post_deploy: list[CfnginHookDefinitionModel]
    """Hooks to run after a deploy action."""

    post_destroy: list[CfnginHookDefinitionModel]
    """Hooks to run after a destroy action."""

    pre_deploy: list[CfnginHookDefinitionModel]
    """Hooks to run before a deploy action."""

    pre_destroy: list[CfnginHookDefinitionModel]
    """Hooks to run before a destroy action."""

    service_role: str | None
    """IAM role for CloudFormation to use."""

    stacks: list[CfnginStackDefinitionModel]
    """Stacks to be processed."""

    sys_path: Path | None
    """Relative or absolute path to use as the work directory."""

    tags: dict[str, str] | None
    """Tags to apply to all resources."""

    template_indent: int
    """Spaces to use per-indent level when outputting a template to json."""

    def __init__(
        self,
        data: CfnginConfigDefinitionModel,
        *,
        path: Path | None = None,
        work_dir: Path | None = None,
    ) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.
            work_dir: Working directory.

        """
        super().__init__(data, path=path)

        self.cfngin_bucket = self._data.cfngin_bucket
        self.cfngin_bucket_region = self._data.cfngin_bucket_region
        if self._data.cfngin_cache_dir:
            self.cfngin_cache_dir = self._data.cfngin_cache_dir
        elif work_dir:
            self.cfngin_cache_dir = work_dir / "cache"
        elif path:
            self.cfngin_cache_dir = path.parent / ".runway" / "cache"
        else:
            self.cfngin_cache_dir = Path().cwd() / ".runway" / "cache"
        self.log_formats = self._data.log_formats
        self.lookups = self._data.lookups
        self.mappings = self._data.mappings
        self.namespace = self._data.namespace
        self.namespace_delimiter = self._data.namespace_delimiter
        self.package_sources = self._data.package_sources
        self.persistent_graph_key = self._data.persistent_graph_key
        self.post_deploy = cast("list[CfnginHookDefinitionModel]", self._data.post_deploy)
        self.post_destroy = cast("list[CfnginHookDefinitionModel]", self._data.post_destroy)
        self.pre_deploy = cast("list[CfnginHookDefinitionModel]", self._data.pre_deploy)
        self.pre_destroy = cast("list[CfnginHookDefinitionModel]", self._data.pre_destroy)
        self.service_role = self._data.service_role
        self.stacks = cast("list[CfnginStackDefinitionModel]", self._data.stacks)
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
    def find_config_file(  # type: ignore
        cls, path: Path | None = None, *, exclude: list[str] | None = None
    ) -> list[Path]:
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
        result: list[Path] = []
        exclude.extend(cls.EXCLUDE_LIST)

        yml_files = list(path.glob("*.yml"))
        yml_files.extend(list(path.glob("*.yaml")))

        for f in yml_files:
            if re.match(cls.EXCLUDE_REGEX, f.name) or f.name in exclude or f.name.startswith("."):
                continue  # cov: ignore
            result.append(f)
        result.sort()
        return result

    @classmethod
    def parse_file(
        cls,
        *,
        path: Path | None = None,
        file_path: Path | None = None,
        parameters: MutableMapping[str, Any] | None = None,
        work_dir: Path | None = None,
        **kwargs: Any,
    ) -> CfnginConfig:
        """Parse a YAML file to create a config object.

        Args:
            path: The path to search for a config file.
            file_path: Exact path to a file to parse.
            parameters: Values to use when resolving a raw config.
            work_dir: Explicit working directory.
            **kwargs: Arbitrary keyword arguments.

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
                work_dir=work_dir,
                **kwargs,
            )
        if path:
            found = cls.find_config_file(path)
            if len(found) > 1:
                raise ValueError(f"more than one config files found: {found}")
            return cls.parse_file(
                file_path=found[0],
                parameters=parameters or {},
                work_dir=work_dir,
                **kwargs,
            )
        raise ValueError("must provide path or file_path")

    @classmethod
    def parse_obj(
        cls, obj: Any, *, path: Path | None = None, work_dir: Path | None = None
    ) -> CfnginConfig:
        """Parse a python object.

        Args:
            obj: A python object to parse as a CFNgin config.
            path: The path to the config file that was parsed into the object.
            work_dir: Working directory.

        """
        return cls(CfnginConfigDefinitionModel.model_validate(obj), path=path, work_dir=work_dir)

    @classmethod
    def parse_raw(
        cls,
        data: str,
        *,
        parameters: MutableMapping[str, Any] | None = None,
        path: Path | None = None,
        skip_package_sources: bool = False,
        work_dir: Path | None = None,
    ) -> CfnginConfig:
        """Parse raw data.

        Args:
            data: The raw data to parse.
            parameters: Values to use when resolving a raw config.
            path: The path to search for a config file.
            skip_package_sources: Skip processing package sources.
            work_dir: Explicit working directory.

        """
        if not parameters:
            parameters = {}
        pre_rendered = cls.resolve_raw_data(data, parameters=parameters)
        if skip_package_sources:
            return cls.parse_obj(yaml.safe_load(pre_rendered))
        config_dict = yaml.safe_load(
            cls.process_package_sources(pre_rendered, parameters=parameters, work_dir=work_dir)
        )
        return cls.parse_obj(config_dict, path=path)

    @classmethod
    def process_package_sources(
        cls,
        raw_data: str,
        *,
        parameters: MutableMapping[str, Any] | None = None,
        work_dir: Path | None = None,
    ) -> str:
        """Process the package sources defined in a rendered config.

        Args:
            raw_data: Raw configuration data.
            cache_dir: Directory to use when caching remote sources.
            parameters: Values to use when resolving a raw config.
            work_dir: Explicit working directory.

        """
        config: dict[str, Any] = yaml.safe_load(raw_data) or {}
        processor = SourceProcessor(
            sources=CfnginPackageSourcesDefinitionModel.model_validate(
                config.get("package_sources", {})
            ),
            cache_dir=Path(
                config.get("cfngin_cache_dir", (work_dir or Path().cwd() / ".runway") / "cache")
            ),
        )
        processor.get_package_sources()
        if processor.configs_to_merge:
            for i in processor.configs_to_merge:
                LOGGER.debug("merging in remote config: %s", i)
                with i.open("rb") as opened_file:
                    config = merge_dicts(yaml.safe_load(opened_file), config)
            return cls.resolve_raw_data(yaml.dump(config), parameters=parameters or {})
        return raw_data

    @staticmethod
    def resolve_raw_data(
        raw_data: str, *, parameters: MutableMapping[str, Any] | None = None
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


class RunwayConfig(BaseConfig[RunwayConfigDefinitionModel]):
    """Python representation of a Runway config file."""

    ACCEPTED_NAMES = ["runway.yml", "runway.yaml"]

    deployments: list[RunwayDeploymentDefinition]
    file_path: Path
    future: RunwayFutureDefinitionModel
    ignore_git_branch: bool
    runway_version: SpecifierSet | None
    tests: list[RunwayTestDefinition]
    variables: RunwayVariablesDefinition

    def __init__(self, data: RunwayConfigDefinitionModel, *, path: Path | None = None) -> None:
        """Instantiate class.

        Args:
            data: The data model of the config file.
            path: Path to the config file.

        """
        super().__init__(data, path=path)
        self.deployments = [RunwayDeploymentDefinition(d) for d in self._data.deployments]
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
        path: Path | None = None,
        file_path: Path | None = None,
        **kwargs: Any,
    ) -> RunwayConfig:
        """Parse a YAML file to create a config object.

        Args:
            path: The path to search for a config file.
            file_path: Exact path to a file to parse.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ConfigNotFound: Provided config file was not found.
            ValueError: path and file_path were both excluded.

        """
        if file_path:
            if not file_path.is_file():
                raise ConfigNotFound(path=file_path)
            return cls.parse_obj(yaml.safe_load(file_path.read_text()), path=file_path, **kwargs)
        if path:
            return cls.parse_file(file_path=cls.find_config_file(path), **kwargs)
        raise ValueError("must provide path or file_path")

    @classmethod
    def parse_obj(cls, obj: Any, *, path: Path | None = None) -> RunwayConfig:
        """Parse a python object into a config object.

        Args:
            obj: The object to be parsed.
            path: Path to the file the object was parsed from.

        """
        return cls(RunwayConfigDefinitionModel.model_validate(obj), path=path)
