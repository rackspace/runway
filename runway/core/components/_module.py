"""Runway module object."""
from __future__ import annotations

import concurrent.futures
import json
import logging
import multiprocessing
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

import yaml

from ..._logging import PrefixAdaptor
from ...compat import cached_property
from ...config.components.runway import RunwayVariablesDefinition
from ...config.models.runway import (
    RunwayEnvVarsType,
    RunwayFutureDefinitionModel,
    RunwayVariablesDefinitionModel,
)
from ...utils import change_dir, flatten_path_lists, merge_dicts
from ..providers import aws
from ._module_path import ModulePath
from ._module_type import RunwayModuleType

if TYPE_CHECKING:
    from ..._logging import RunwayLogger
    from ...config.components.runway import (
        RunwayDeploymentDefinition,
        RunwayModuleDefinition,
    )
    from ...config.models.runway import RunwayEnvironmentsType
    from ...context import RunwayContext
    from ..type_defs import RunwayActionTypeDef

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


class Module:
    """Runway module."""

    ctx: RunwayContext
    logger: PrefixAdaptor
    name: str

    def __init__(
        self,
        context: RunwayContext,
        definition: RunwayModuleDefinition,
        deployment: RunwayDeploymentDefinition = None,
        future: RunwayFutureDefinitionModel = None,
        variables: RunwayVariablesDefinition = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.
            definition: A single module definition.
            deployment: Deployment that this
                module is a part of.
            future: Future functionality
                configuration.
            variables: Runway variables.

        """
        self.__deployment = deployment
        self.__future = future or RunwayFutureDefinitionModel()
        self.__variables = variables or RunwayVariablesDefinition(
            RunwayVariablesDefinitionModel()
        )
        self.ctx = context.copy()  # each module has it's own instance of context
        definition.resolve(self.ctx, variables=variables)
        self.definition = definition
        self.name = self.definition.name
        self.logger = PrefixAdaptor(self.fqn, LOGGER)

    @cached_property
    def child_modules(self) -> List[Module]:
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
    def environment_matches_defined(self) -> Optional[bool]:
        """Environment matches one of the defined environments.

        Will return None if there is nothing defined for the current environment.

        """
        return validate_environment(self.ctx, self.environments, logger=self.logger)

    @cached_property
    def environments(self) -> RunwayEnvironmentsType:
        """Environments defined for the deployment and module."""
        tmp: RunwayEnvironmentsType = self.definition.environments
        if self.__deployment:
            tmp = merge_dicts(self.__deployment.environments, tmp)
        if self.opts_from_file:
            tmp = merge_dicts(tmp, self.opts_from_file.get("environments", {}))
        return tmp

    @cached_property
    def fqn(self):
        """Fully qualified name."""
        if not self.__deployment:
            return self.name
        return f"{self.__deployment.name}.{self.name}"

    @cached_property
    def opts_from_file(self) -> Dict[str, Any]:
        """Load module options from local file."""
        opts_file = self.path.module_root / "runway.module.yml"
        if opts_file.is_file():
            self.logger.verbose("module-level config file found")
            return yaml.safe_load(opts_file.read_text())
        return {}

    @cached_property
    def path(self) -> ModulePath:  # lazy load the path
        """Return resolve module path."""
        return ModulePath.parse_obj(self.definition, deploy_environment=self.ctx.env)

    @cached_property
    def payload(self) -> Dict[str, Any]:  # lazy load the payload
        """Return payload to be passed to module class handler class."""
        payload: Dict[str, Any] = {}
        if self.__deployment:
            payload.update(
                {
                    "options": self.__deployment.module_options,
                    "parameters": self.__deployment.parameters,
                }
            )
        payload = merge_dicts(payload, self.definition.data)
        payload = merge_dicts(payload, self.opts_from_file)
        payload["explicitly_enabled"] = bool(self.environment_matches_defined)
        self.__merge_env_vars(payload.pop("env_vars", {}))
        return payload

    @cached_property
    def should_skip(self) -> bool:
        """Whether the module should be skipped by Runway."""
        if isinstance(self.environment_matches_defined, bool):
            return not self.environment_matches_defined
        return False

    @cached_property
    def type(self) -> RunwayModuleType:
        """Determine Runway module type."""
        return RunwayModuleType(
            path=self.path.module_root,
            class_path=self.definition.class_path,
            type_str=self.definition.type,
        )

    @cached_property
    def use_async(self) -> bool:
        """Whether to use asynchronous method."""
        return bool(self.definition.child_modules and self.ctx.use_concurrent)

    def deploy(self) -> None:
        """Deploy the module.

        High level method for running a module.

        """
        if not self.child_modules:
            return self.run("deploy")
        if self.use_async:
            return self.__async("deploy")
        return self.__sync("deploy")

    def destroy(self) -> None:
        """Destroy the module.

        High level method for running a module.

        """
        if not self.child_modules:
            return self.run("destroy")
        if self.use_async:
            return self.__async("destroy")
        return self.__sync("destroy")

    def init(self) -> None:
        """Initialize/bootstrap module.

        High level method for running a deployment.

        """
        if not self.child_modules:
            return self.run("init")
        if self.use_async:
            return self.__async("init")
        return self.__sync("init")

    def plan(self) -> None:
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

    def run(self, action: RunwayActionTypeDef) -> None:
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
                self.ctx, module_root=self.path.module_root, **self.payload
            )
            if hasattr(inst, action):
                inst[action]()
            else:
                self.logger.error('"%s" is missing method "%s"', inst, action)
                sys.exit(1)
        self.logger.success(
            "processing module in %s (complete)", self.ctx.env.aws_region
        )

    def __async(self, action: RunwayActionTypeDef) -> None:
        """Execute asynchronously.

        Args:
            action: Name of action to run.

        """
        self.logger.info(
            "processing modules in parallel... (output will be interwoven)"
        )
        # Can't use threading or ThreadPoolExecutor here because
        # we need to be able to do things like `cd` which is not
        # thread safe.
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.ctx.env.max_concurrent_modules,
            mp_context=multiprocessing.get_context("fork"),
        ) as executor:
            futures = [
                executor.submit(child.run, *[action]) for child in self.child_modules
            ]
        for job in futures:
            job.result()  # raise exceptions / exit as needed

    def __sync(self, action: RunwayActionTypeDef) -> None:
        """Execute synchronously.

        Args:
            action: Name of action to run.

        """
        self.logger.info("processing modules sequentially...")
        for module in self.child_modules:
            module.run(action)

    def __merge_env_vars(self, env_vars: RunwayEnvVarsType) -> None:
        """Merge defined env_vars into context.env_vars."""
        if env_vars:
            resolved_env_vars = flatten_path_lists(env_vars, str(self.ctx.env.root_dir))
            if resolved_env_vars:
                self.logger.verbose(
                    "environment variable overrides are being applied to this module"
                )
                self.logger.debug(
                    "environment variable overrides: %s", resolved_env_vars
                )
                self.ctx.env.vars = merge_dicts(self.ctx.env.vars, resolved_env_vars)

    @classmethod
    def run_list(
        cls,
        action: RunwayActionTypeDef,
        context: RunwayContext,
        modules: List[RunwayModuleDefinition],
        variables: RunwayVariablesDefinition,
        deployment: RunwayDeploymentDefinition = None,
        future: Optional[RunwayFutureDefinitionModel] = None,
    ) -> None:
        """Run a list of modules.

        Args:
            action: Name of action to run.
            context: Runway context.
            modules: List of modules to run.
            variables: Variable definition for resolving lookups in the module.
            deployment: Deployment the modules are a part of.
            future: Future functionality configuration.

        """
        for module in modules:
            cls(
                context=context,
                definition=module,
                deployment=deployment,
                future=future,
                variables=variables,
            )[action]()

    def __getitem__(self, key: str) -> Any:
        """Make the object subscriptable.

        Args:
            key: Attribute to get.

        """
        return getattr(self, key)


def validate_environment(
    context: RunwayContext,
    env_def: Optional[Union[bool, Dict[str, Any], int, str, List[str]]],
    logger: Union[PrefixAdaptor, RunwayLogger] = LOGGER,
) -> Optional[bool]:
    """Check if an environment should be deployed to.

    Args:
        context: Runway context object.
        env_def: Runway module definition.
        logger: Logger to log messages to.

    Returns:
        Booleon value of whether to deploy or not.

    """
    if isinstance(env_def, bool) or not env_def:
        if env_def is True:
            logger.verbose("explicitly enabled")
        elif env_def is False:
            logger.info("skipped; explicitly disabled")
        else:
            logger.verbose("environment not defined; module will determine deployment")
            env_def = None
        return cast(Optional[bool], env_def)
    if isinstance(env_def, dict):
        if context.env.name not in env_def:
            logger.info("skipped; environment not in definition")
            return False
        return validate_environment(
            context, cast(Any, env_def.get(context.env.name, False)), logger=logger
        )

    account = aws.AccountDetails(context)
    accepted_values = [
        f"{account.id}/{context.env.aws_region}",
        account.id,
        context.env.aws_region,
        int(account.id),
    ]
    result = False

    if isinstance(env_def, (int, str)):
        logger.debug('checking if "%s" in %s', env_def, accepted_values)
        result = env_def in accepted_values
    elif isinstance(env_def, list):  # type: ignore
        logger.debug("checking if any(%s in %s)", env_def, accepted_values)
        result = any(val in env_def for val in accepted_values)
    else:
        logger.warning('skipped; unsupported type for environments "%s"', type(env_def))
        return False

    if not result:
        logger.info("skipped; account_id/region mismatch")
    return result
