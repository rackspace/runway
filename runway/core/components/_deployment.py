"""Runway deployment object."""
from __future__ import annotations

import concurrent.futures
import logging
import multiprocessing
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..._logging import PrefixAdaptor
from ...compat import cached_property
from ...config.components.runway import RunwayVariablesDefinition
from ...config.models.runway import (
    RunwayAssumeRoleDefinitionModel,
    RunwayFutureDefinitionModel,
)
from ...exceptions import UnresolvedVariable
from ...utils import flatten_path_lists, merge_dicts
from ..providers import aws
from ._module import Module

if TYPE_CHECKING:
    from ...config.components.runway import RunwayDeploymentDefinition
    from ...context import RunwayContext
    from ..type_defs import RunwayActionTypeDef


LOGGER = logging.getLogger(__name__.replace("._", "."))


class Deployment:
    """Runway deployment."""

    def __init__(
        self,
        context: RunwayContext,
        definition: RunwayDeploymentDefinition,
        future: Optional[RunwayFutureDefinitionModel] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object.
            definition: A single deployment definition.
            future: Future functionality configuration.
            variables: Runway variables.

        """
        self._future = future or RunwayFutureDefinitionModel()
        self._variables = variables or RunwayVariablesDefinition.parse_obj({})
        self.definition = definition
        self.ctx = context
        self.name = self.definition.name
        self.logger = PrefixAdaptor(self.name, LOGGER)
        self.__merge_env_vars()

    @property
    def assume_role_config(self) -> Dict[str, Union[bool, int, str]]:
        """Parse the definition to get assume role arguments."""
        assume_role = self.definition.assume_role
        if not assume_role:
            self.logger.debug(
                "assume_role not configured for deployment: %s", self.name
            )
            return {}
        if isinstance(assume_role, str):  # type: ignore
            self.logger.debug("role found: %s", assume_role)
            assume_role = RunwayAssumeRoleDefinitionModel(arn=assume_role)
        elif isinstance(assume_role, dict):  # type: ignore
            assume_role = RunwayAssumeRoleDefinitionModel.parse_obj(assume_role)
        if not assume_role.arn:
            self.logger.debug(
                "assume_role not configured for deployment: %s", self.name
            )
            return {}
        return {
            "duration_seconds": assume_role.duration,
            "revert_on_exit": assume_role.post_deploy_env_revert,
            "role_arn": assume_role.arn,
            "session_name": assume_role.session_name,
        }

    @property
    def env_vars_config(self) -> Dict[str, str]:
        """Parse the definition to get the correct env_vars configuration."""
        try:
            if not self.definition.env_vars:
                return {}
        except UnresolvedVariable:
            self.definition._env_vars.resolve(  # pylint: disable=protected-access
                self.ctx, variables=self._variables
            )
        return flatten_path_lists(self.definition.env_vars, str(self.ctx.env.root_dir))

    @cached_property
    def regions(self) -> List[str]:
        """List of regions this deployment is associated with."""
        return self.definition.parallel_regions or self.definition.regions

    @cached_property
    def use_async(self) -> bool:
        """Whether to use asynchronous method."""
        return bool(self.definition.parallel_regions and self.ctx.use_concurrent)

    def deploy(self) -> None:
        """Deploy the deployment.

        High level method for running a deployment.

        """
        self.logger.verbose(
            "attempting to deploy to region(s): %s", ", ".join(self.regions)
        )
        if self.use_async:
            return self.__async("deploy")
        return self.__sync("deploy")

    def destroy(self) -> None:
        """Destroy the deployment.

        High level method for running a deployment.

        """
        self.logger.verbose(
            "attempting to destroy in region(s): %s", ", ".join(self.regions)
        )
        if self.use_async:
            return self.__async("destroy")
        return self.__sync("destroy")

    def init(self) -> None:
        """Initialize/bootstrap deployment.

        High level method for running a deployment.

        """
        self.logger.verbose(
            "attempting to initialize region(s): %s", ", ".join(self.regions)
        )
        if self.use_async:
            return self.__async("init")
        return self.__sync("init")

    def plan(self) -> None:
        """Plan for the next deploy of the deployment.

        High level method for running a deployment.

        """
        self.logger.verbose(
            "attempting to plan for the next deploy to region(s): %s",
            ", ".join(self.regions),
        )
        if self.use_async:
            self.logger.notice(
                "processing of regions will be done in parallel during deploy/destroy"
            )
        return self.__sync("plan")

    def run(self, action: RunwayActionTypeDef, region: str) -> None:
        """Run a single deployment in a single region.

        Low level API access to run a deployment object.

        Args:
            action: Action to run (deploy, destroy, plan, etc.)
            region: AWS region to run in.

        """
        context = self.ctx.copy() if self.use_async else self.ctx
        context.command = action
        context.env.aws_region = region

        with aws.AssumeRole(context, **self.assume_role_config):
            self.definition.resolve(context, variables=self._variables)
            self.validate_account_credentials(context)
            Module.run_list(
                action=action,
                context=context,
                deployment=self.definition,
                future=self._future,
                modules=self.definition.modules,
                variables=self._variables,
            )

    def validate_account_credentials(
        self, context: Optional[RunwayContext] = None
    ) -> None:
        """Exit if requested deployment account doesn't match credentials.

        Args:
            context: Context object.

        Raises:
            SystemExit: AWS Account associated with the current credentials
                did not match the defined criteria.

        """
        account = aws.AccountDetails(context or self.ctx)
        if self.definition.account_id:
            if self.definition.account_id != account.id:
                self.logger.error(
                    'current AWS account "%s" does not match '
                    'required account "%s" in Runway config',
                    account.id,
                    self.definition.account_id,
                )
                sys.exit(1)
            self.logger.info(
                "verified current AWS account matches required " 'account id "%s"',
                self.definition.account_id,
            )
        if self.definition.account_alias:
            if self.definition.account_alias not in account.aliases:
                self.logger.error(
                    'current AWS account aliases "%s" do not match '
                    'required account alias "%s" in Runway config.',
                    ",".join(account.aliases),
                    self.definition.account_alias,
                )
                sys.exit(1)
            self.logger.info(
                'verified current AWS account alias matches required alias "%s"',
                self.definition.account_alias,
            )

    def __merge_env_vars(self) -> None:
        """Merge defined env_vars into context.env_vars."""
        if self.env_vars_config:
            self.logger.verbose(
                "environment variable overrides are being applied to this deployment"
            )
            self.logger.debug(
                "environment variable overrides: %s", self.env_vars_config
            )
            self.ctx.env.vars = merge_dicts(self.ctx.env.vars, self.env_vars_config)

    def __async(self, action: RunwayActionTypeDef) -> None:
        """Execute asynchronously.

        Args:
            action: Name of action to run.

        """
        self.logger.info(
            "processing regions in parallel... (output will be interwoven)"
        )
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.ctx.env.max_concurrent_regions,
            mp_context=multiprocessing.get_context("fork"),
        ) as executor:
            futures = [
                executor.submit(self.run, *[action, region]) for region in self.regions
            ]
        for job in futures:
            job.result()  # raise exceptions / exit as needed

    def __sync(self, action: RunwayActionTypeDef) -> None:
        """Execute synchronously.

        Args:
            action: Name of action to run.

        """
        self.logger.info("processing regions sequentially...")
        for region in self.regions:
            self.logger.verbose("processing AWS region: %s", region)
            self.run(action, region)

    @classmethod
    def run_list(
        cls,
        action: RunwayActionTypeDef,
        context: RunwayContext,
        deployments: List[RunwayDeploymentDefinition],
        future: RunwayFutureDefinitionModel,
        variables: RunwayVariablesDefinition,
    ) -> None:
        """Run a list of deployments.

        Args:
            action: Name of action to run.
            context: Runway context.
            deployments: List of deployments to run.
            future: Future definition.
            variables: Runway variables for lookup resolution.

        """
        for definition in deployments:
            definition.resolve(context, variables=variables, pre_process=True)
            deployment = cls(
                context=context,
                definition=definition,
                future=future,
                variables=variables,
            )
            LOGGER.info("")
            LOGGER.info("")
            deployment.logger.notice("processing deployment (in progress)")
            if not definition.modules:
                deployment.logger.warning("skipped; no modules found in definition")
                continue
            cls(
                context=context,
                definition=definition,
                future=future,
                variables=variables,
            )[action]()
            deployment.logger.success("processing deployment (complete)")

    def __getitem__(self, name: str) -> Any:
        """Make the object subscriptable.

        Args:
            name: Attribute to get.

        """
        return getattr(self, name)
