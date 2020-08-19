"""Runway module object."""
import json
import logging
import sys
from typing import (  # noqa pylint: disable=W
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)

import six
import yaml

from ..._logging import PrefixAdaptor
from ...config import FutureDefinition, VariablesDefinition
from ...path import Path as ModulePath
from ...runway_module_type import RunwayModuleType
from ...util import (
    cached_property,
    change_dir,
    merge_dicts,
    merge_nested_environment_dicts,
)
from ..providers import aws

if sys.version_info.major > 2:
    import concurrent.futures
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

if TYPE_CHECKING:
    from ...config import DeploymentDefinition, ModuleDefinition  # pylint: disable=W
    from ...context import Context  # pylint: disable=W

LOGGER = logging.getLogger(__name__.replace("._", "."))


class Module(object):
    """Runway module."""

    def __init__(
        self,
        context,  # type: Context
        definition,  # type: ModuleDefinition
        deployment=None,  # type: Optional[DeploymentDefinition]
        future=None,  # type: Optional[FutureDefinition]
        variables=None,  # type: Optional[VariablesDefinition]
    ):
        # type: (...) -> None
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            definition (ModuleDefinition): A single module definition.
            deployment (Optional[DeploymentDefinition]): Deployment that this
                module is a part of.
            future (Optional[FutureDefinition]): Future functionality
                configuration.
            variables (Optional[VariablesDefinition]): Runway variables.

        """
        self.__deployment = deployment
        self.__future = future or FutureDefinition()
        self.__variables = variables or VariablesDefinition()
        self.ctx = context.copy()  # each module has it's own instance of context
        definition.resolve(self.ctx, variables)
        self.definition = definition
        self.name = self.definition.name
        self.logger = PrefixAdaptor(self.fqn, LOGGER)

    @cached_property
    def child_modules(self):
        # type: () -> List['Module']
        """Return child modules."""
        return [
            self.__class__(
                context=self.ctx,
                definition=child,
                deployment=self.__deployment,
                future=self.__future,
                variables=self.__variables,
            )
            for child in self.definition.child_modules
        ]

    @cached_property
    def fqn(self):
        """Fully qualified name."""
        if not self.__deployment:
            return self.name
        return "{}.{}".format(self.__deployment.name, self.name)

    @cached_property
    def path(self):  # lazy load the path
        # type: () -> ModulePath
        """Return resolve module path."""
        return ModulePath(
            self.definition,
            str(self.ctx.env.root_dir),
            str(self.ctx.env.root_dir / ".runway_cache"),
        )

    @cached_property
    def payload(self):  # lazy load the payload
        # type: () -> Dict[str, Any]
        """Return payload to be passed to module class handler class."""
        payload = {"environments": {}}
        if self.__deployment:
            payload.update(
                {
                    "environments": self.__deployment.environments,
                    "options": self.__deployment.module_options,
                    "parameters": self.__deployment.parameters,
                }
            )
        payload = merge_dicts(payload, self.definition.data)
        payload = merge_dicts(payload, self.__load_opts_from_file())
        payload["environment"] = payload["environments"].get(self.ctx.env.name, {})
        self.__merge_env_vars(payload.pop("env_vars", {}))
        return payload

    @cached_property
    def should_skip(self):
        # type: () -> bool
        """Whether the module should be skipped by Runway."""
        if (
            isinstance(self.payload["environment"], dict)
            and not self.__future.strict_environments
        ):
            return self.__handle_deprecated_environmet()
        is_valid = validate_environment(
            self.ctx,
            self.payload["environments"],
            logger=self.logger,
            strict=self.__future.strict_environments,
        )
        self.payload["environment"] = is_valid
        if isinstance(is_valid, bool):
            return not is_valid
        return False

    @cached_property
    def type(self):
        # type: () -> RunwayModuleType
        """Determine Runway module type."""
        return RunwayModuleType(
            path=self.path.module_root,
            class_path=self.payload.get("class_path"),
            type_str=self.payload.get("type"),
        )

    @cached_property
    def use_async(self):
        # type: () -> bool
        """Whether to use asynchronous method."""
        return bool(self.definition.child_modules and self.ctx.use_concurrent)

    def deploy(self):
        # type: () -> None
        """Deploy the module.

        High level method for running a module.

        """
        if not self.child_modules:
            return self.run("deploy")
        if self.use_async:
            return self.__async("deploy")
        return self.__sync("deploy")

    def destroy(self):
        # type: () -> None
        """Destroy the module.

        High level method for running a module.

        """
        if not self.child_modules:
            return self.run("destroy")
        if self.use_async:
            return self.__async("destroy")
        return self.__sync("destroy")

    def plan(self):
        # type: () -> None
        """Plan for the next deploy of the module.

        High level method for running a module.

        """
        if not self.child_modules:
            return self.run("plan")
        if self.use_async:
            self.logger.info(
                "processing of modules will be done in parallel during deploy/destroy"
            )
        return self.__sync("plan")

    def run(self, action):
        # type: (str) -> None
        """Run a single module.

        Low level API access to run a module object.

        Args:
            action: Name of action to run.

        """
        LOGGER.info("")
        self.logger.notice(
            "processing module in %s (in progress)", self.ctx.env.aws_region
        )
        self.logger.verbose("module payload: %s", json.dumps(self.payload))
        if self.should_skip:
            return
        with change_dir(self.path.module_root):
            # dynamically load the particular module's class, 'get' the method
            # associated with the command, and call the method.
            inst = self.type.module_class(
                context=self.ctx, path=self.path.module_root, options=self.payload
            )
            if hasattr(inst, action):
                inst[action]()
            else:
                self.logger.error('"%s" is missing method "%s"', inst, action)
                sys.exit(1)
        self.logger.success(
            "processing module in %s (complete)", self.ctx.env.aws_region
        )

    def __async(self, action):
        # type: (str) -> None
        """Execute asynchronously.

        Args:
            action (str): Name of action to run.

        """
        self.logger.info(
            "processing modules in parallel... (output will be interwoven)"
        )
        # Can't use threading or ThreadPoolExecutor here because
        # we need to be able to do things like `cd` which is not
        # thread safe.
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.ctx.env.max_concurrent_modules
        )
        futures = [
            executor.submit(child.run, *[action]) for child in self.child_modules
        ]
        concurrent.futures.wait(futures)
        for job in futures:
            job.result()  # raise exceptions / exit as needed

    def __sync(self, action):
        # type: (str) -> None
        """Execute synchronously.

        Args:
            action (str): Name of action to run.

        """
        self.logger.info("processing modules sequentially...")
        for module in self.child_modules:
            module.run(action)

    def __load_opts_from_file(self):
        # type: () -> Dict[str, Any]
        """Load module options from local file."""
        opts_file = Path(self.path.module_root) / "runway.module.yml"
        if opts_file.is_file():
            self.logger.verbose("module-level config file found")
            return yaml.safe_load(opts_file.read_text())
        return {}

    def __merge_env_vars(self, env_vars):
        # type: (Dict[str, Any]) -> None
        """Merge defined env_vars into context.env_vars."""
        if env_vars:
            resolved_env_vars = merge_nested_environment_dicts(
                env_vars,
                env_name=self.ctx.env.name,
                env_root=str(self.ctx.env.root_dir),
            )
            if resolved_env_vars:
                self.logger.verbose(
                    "environment variable overrides are being applied to this module"
                )
                self.logger.debug(
                    "environment variable overrides: %s", resolved_env_vars
                )
                self.ctx.env.vars = merge_dicts(self.ctx.env_vars, resolved_env_vars)

    def __handle_deprecated_environmet(self):
        # type: () -> None
        """Handle deprecated environments value."""
        self.payload["parameters"].update(self.payload["environment"])
        if self.payload["parameters"]:
            self.payload["environment"] = True
        return False

    @classmethod
    def run_list(
        cls,
        action,  # type: str
        context,  # type: Context
        modules,  # type: List[ModuleDefinition]
        variables,  # type: VariablesDefinition
        deployment=None,  # type: Optional[DeploymentDefinition]
        future=None,  # type: Optional[FutureDefinition]
    ):
        # type: (...) -> None
        """Run a list of modules.

        Args:
            action: Name of action to run.
            context: Runway context.
            modules: List of modules to run.
            variables: Variable definition for resolving lookups in the module.
            deployment: Deployment the modules are a part of.
            future (Optional[FutureDefinition]): Future functionality
                configuration.

        """
        for module in modules:
            cls(
                context=context,
                definition=module,
                deployment=deployment,
                future=future,
                variables=variables,
            )[action]()

    def __getitem__(self, key):
        """Make the object subscriptable.

        Args:
            key (str): Attribute to get.

        Returns:
            Any

        """
        return getattr(self, key)


def validate_environment(context, env_def, logger=None, strict=False):
    """Check if an environment should be deployed to.

    Args:
        context (Context): Runway context object.
        module (ModuleDefinition): Runway module definition.
        logger (Optional[logging.Logger]): Logger to log messages to.
        strict (bool): Wether to consider the current environment missing from
            definition as a failure.

    Returns:
        Union[bool, NoneType]: Booleon value of wether to deploy or not.

    """
    logger = logger or LOGGER
    if isinstance(env_def, bool) or not env_def:
        if env_def is True:
            logger.verbose("explicitly enabled")
        elif env_def is False:
            logger.info("skipped; explicitly disabled")
        else:
            logger.verbose("environment not defined; module will determine deployment")
            env_def = None
        return env_def
    if isinstance(env_def, dict):
        if context.env.name not in env_def:
            if strict:
                logger.info("skipped; environment not in definition")
                return False
            logger.info(
                "environment not in definition; module will determine deployment"
            )
            return None
        return validate_environment(
            context, env_def.get(context.env.name, False), logger=logger, strict=strict
        )

    account = aws.AccountDetails(context)
    accepted_values = [
        "{}/{}".format(account.id, context.env.aws_region),
        account.id,
        context.env.aws_region,
        int(account.id),
    ]
    result = False

    if isinstance(env_def, (int, six.string_types)):
        logger.debug('checking if "%s" in %s', env_def, accepted_values)
        result = env_def in accepted_values
    elif isinstance(env_def, list):
        logger.debug("checking if any(%s in %s)", env_def, accepted_values)
        result = any(val in env_def for val in accepted_values)
    else:
        logger.warning('skipped; unsupported type for environments "%s"', type(env_def))
        return False

    if not result:
        logger.info("skipped; account_id/region mismatch")
    return result
