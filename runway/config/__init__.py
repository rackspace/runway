"""CFNgin config."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import copy
import logging
import sys
from abc import abstractclassmethod
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, validator

from ..cfngin import exceptions
from ..cfngin.lookups import register_lookup_handler
from ..cfngin.util import SourceProcessor, merge_map
from ..exceptions import ConfigNotFound
from .components.runway import RunwayDeploymentDefinition, RunwayVariablesDefinition
from .models.cfngin import Hook, PackageSources, Stack, Target
from .models.runway import (
    RunwayConfigDefinitionModel,
    RunwayFutureDefinitionModel,
    RunwayTestDefinitionModel,
)

if TYPE_CHECKING:
    from packaging.specifiers import SpecifierSet

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
        self.file_path = path.resolve()

    def dump(
        self,
        *,
        by_alias: bool = False,
        exclude: Optional[List[str]] = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: Optional[List[str]] = None,
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
                exclude=exclude,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                include=include,
            ),
            default_flow_style=False,
        )

    @abstractclassmethod
    def find_config_file(cls, path: Path) -> Optional[Path]:  # noqa: N805
        """Find a config file in the provided path.

        Args:
            path: The path to search for a config file.

        """
        raise NotImplementedError

    @classmethod
    def parse_file(
        cls, *, path: Optional[Path] = None, file_path: Optional[Path], **kwargs: Any
    ) -> BaseConfig:
        """Parse a YAML file to create a config object.

        Args:
            path: The path to search for a config file.
            file_path: Exact path to a file to parse.

        Raises:
            ConfigNotFound: Provided config file was not found.

        """
        if file_path:
            if not file_path.is_file():
                raise ConfigNotFound(path=path)
            return cls.parse_obj(
                yaml.safe_load(file_path.read_text()), path=file_path, **kwargs
            )
        if path:
            return cls.parse_file(file_path=cls.find_config_file(path), **kwargs)
        raise ValueError("must provide path or file_path")

    @abstractclassmethod
    def parse_obj(cls, obj: Any, *, path: Path) -> BaseConfig:  # noqa: N805
        """Parse a python object into a config object.

        Args:
            obj: The object to be parsed.
            path: Path to the file the object was parsed from.

        """
        raise NotImplementedError


class CfnginConfig(BaseModel):
    """Python representation of a CFNgin config file.

    This is used internally by CFNgin to parse and validate a YAML formatted
    CFNgin configuration file, but can also be used in scripts to generate a
    CFNgin config file before handing it off to CFNgin to build/destroy.

    Example::

        from runway.cfngin.config import dump, Config, Stack

        vpc = Stack({
            "name": "vpc",
            "class_path": "blueprints.VPC"})

        config = Config()
        config.namespace = "prod"
        config.stacks = [vpc]

        print dump(config)

    Attributes:
        cfngin_bucket: Bucket to use for CFNgin resources (e.g.
            CloudFormation templates). May be an empty string.
        cfngin_bucket_region: Explicit region to use for
            ``cfngin_bucket``.
        cfngin_cache_dir: Local directory to use for caching.
        log_formats: Custom formatting for log messages.
        lookups: Register custom lookups.
        mappings: Mappings that will be added to all stacks.
        namespace: Namespace to prepend to everything.
        namespace_delimiter: Character used to separate ``namespace`` and anything
            it prepends.
        package_sources: Remote source locations.
        persistent_graph_key: S3 object key were the persistent graph is stored.
        post_build: Hooks to run after a build action.
        post_destroy: Hooks to run after a destroy action.
        pre_build: Hooks to run before a build action.
        pre_destroy: Hooks to run before a destroy action.
        service_role: IAM role for CloudFormation to use.
        stacks: Stacks to be processed.
        sys_path: Relative or absolute path to use as the work directory.
        tags: Tags to apply to all resources.
        targets: Stag grouping.
        template_indent: Spaces to use per-indent level when outputing a template
            to json.

    """

    cfngin_bucket: Optional[str] = None
    cfngin_bucket_region: Optional[str] = None
    cfngin_cache_dir: Path = Path.cwd() / ".runway" / "cache"
    log_formats: Dict[str, str] = {}  # TODO create model
    lookups: Optional[Dict[str, str]] = {}  # TODO create model
    mappings: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = {}  # TODO create model
    namespace: str
    namespace_delimiter: str = "-"
    package_sources: PackageSources = PackageSources()
    persistent_graph_key: Optional[str] = None
    post_build: List[Hook] = []
    post_destroy: List[Hook] = []
    pre_build: List[Hook] = []
    pre_destroy: List[Hook] = []
    service_role: Optional[str] = None
    stacks: List[Stack] = []
    sys_path: Optional[Path] = None
    tags: Optional[Dict[str, str]] = None
    targets: List[Target] = []
    template_indent: int = 4

    def dump(
        self,
        *,
        by_alias: bool = False,
        exclude: Optional[List[str]] = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: Optional[List[str]] = None,
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
            self.dict(
                by_alias=by_alias,
                exclude=exclude,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                include=include,
            ),
            default_flow_style=False,
        )

    def load(self) -> None:
        """Load config options into the current environment/session."""
        if self.sys_path:
            LOGGER.debug("appending to sys.path: %s", self.sys_path)
            sys.path.append(str(self.sys_path))
            LOGGER.debug("sys.path: %s", sys.path)
        if self.lookups:
            for key, handler in self.lookups.items():
                register_lookup_handler(key, handler)

    @validator("cfngin_cache_dir", "sys_path")
    def _resolve_path_fields(cls, v: Optional[Path]) -> Optional[Path]:  # noqa: N805
        """Resolve sys_path."""
        return v.resolve() if v else v

    @validator("stacks", pre=True)
    def _validate_unique_stack_names(
        cls, stacks: List[Stack]  # noqa: N805
    ) -> List[Stack]:
        """Validate that each stack has a unique name."""
        stack_names = [stack.get("name") for stack in stacks]
        if len(set(stack_names)) != len(stack_names):
            for i, name in enumerate(stack_names):
                if stack_names.count(name) != 1:
                    raise ValueError(f"Duplicate stack {name} found at index {i}")
        return stacks

    @classmethod
    def parse_file(
        cls, path: Path, *, parameters: Optional[Dict[str, Any]] = None
    ) -> CfnginConfig:
        """Parse a file."""
        return cls.parse_raw(path.read_text(), parameters=parameters or {})

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]) -> CfnginConfig:
        """Parse a python object."""
        for tlk in [
            "stacks",
            "pre_build",
            "post_build",
            "pre_destroy",
            "post_destroy",
        ]:
            tlv = obj.get(tlk)
            if isinstance(tlv, dict):
                tmp_list = []
                for key, value in tlv.items():
                    tmp_dict = copy.deepcopy(value)
                    if tlk == "stacks":
                        tmp_dict["name"] = key
                    tmp_list.append(tmp_dict)
                obj[tlk] = tmp_list
        return super().parse_obj(obj)

    @classmethod
    def parse_raw(
        cls,
        data: str,
        *,
        parameters: Optional[Dict[str, Any]] = None,
        skip_package_sources: bool = False
    ) -> CfnginConfig:
        """Parse raw data."""
        if not parameters:
            parameters = {}
        pre_rendered = cls.render_raw_data(data, parameters=parameters)
        if skip_package_sources:
            return cls.parse_obj(yaml.safe_load(pre_rendered))
        config_dict = yaml.safe_load(
            cls.process_package_sources(pre_rendered, parameters=parameters)
        )
        return cls.parse_obj(config_dict)

    @classmethod
    def process_package_sources(
        cls, raw_data: str, *, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process the package sources defined in a rendered config."""
        config = yaml.safe_load(raw_data)
        processor = SourceProcessor(
            sources=PackageSources.parse_obj(config.get("package_sources", {})),
            cache_dir=config.get("cfngin_cache_dir"),
        )
        processor.get_package_sources()
        if processor.configs_to_merge:
            for i in processor.configs_to_merge:
                LOGGER.debug("merging in remote config: %s", i)
                config = merge_map(yaml.safe_load(open(i)), config)
            return cls.render_raw_data(str(config), parameters=parameters or {})
        return raw_data

    @staticmethod
    def render_raw_data(
        raw_data: str, *, parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render raw data."""
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

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        """
        return getattr(self, key)


class RunwayConfig(BaseConfig):
    """Python representation of a Runway config file."""

    ACCEPTED_NAMES = ["runway.yml", "runway.yaml"]

    deployments: List[RunwayDeploymentDefinition]
    file_path: Path
    future: RunwayFutureDefinitionModel
    ignore_git_branch: bool
    runway_version: Optional[SpecifierSet]
    tests: List[RunwayTestDefinitionModel]
    variables: RunwayVariablesDefinition
    _data: RunwayConfigDefinitionModel

    def __init__(
        self, data: RunwayConfigDefinitionModel, *, path: Optional[Path] = None,
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
        self.tests = self._data.tests
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
    def parse_obj(cls, obj: Any, *, path: Path) -> RunwayConfig:
        """Parse a python object into a config object.

        Args:
            obj: The object to be parsed.
            path: Path to the file the object was parsed from.

        """
        return cls(RunwayConfigDefinitionModel.parse_obj(obj), path=path)
