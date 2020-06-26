"""Runway deployment object."""
import logging
import sys
from typing import (TYPE_CHECKING, Dict, List,  # noqa pylint: disable=W
                    Optional, Union)

import six

from ...config import FutureDefinition, VariablesDefinition
from ...util import (cached_property, merge_dicts,
                     merge_nested_environment_dicts)
from ..providers import aws
from ._module import Module

if sys.version_info.major > 2:
    import concurrent.futures

if TYPE_CHECKING:
    from ...config import DeploymentDefinition  # noqa
    from ...context import Context  # noqa


LOGGER = logging.getLogger(__name__.replace('._', '.'))


class Deployment(object):
    """Runway deployment."""

    def __init__(self,
                 context,  # type: Context
                 definition,  # type: DeploymentDefinition
                 future=None,  # type: Optional[FutureDefinition]
                 variables=None,  # type: VariablesDefinition
                 ):
        # type: (...) -> None
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            definition (DeploymentDefinition): A single deployment definition.
            future (Optional[FutureDefinition]): Future functionality
                configuration.
            variables (VariablesDefinition): Runway variables.

        """
        self._future = future or FutureDefinition()
        self._variables = variables or VariablesDefinition()
        self.definition = definition
        self.ctx = context
        self.name = self.definition.name
        self.__merge_env_vars()

    @property
    def account_alias_config(self):
        # type: () -> Optional[str]
        """Parse the definition to get the correct AWS account alias configuration.

        Returns:
            Optional[str]: Expected AWS account alias for the current context.

        """
        if isinstance(self.definition.account_alias, six.string_types):
            return self.definition.account_alias
        if isinstance(self.definition.account_alias, dict):
            return self.definition.account_alias.get(self.ctx.env.name)
        return None

    @property
    def account_id_config(self):
        # type: () -> Optional[str]
        """Parse the definition to get the correct AWS account ID configuration.

        Returns:
            Optional[str]: Expected AWS account ID for the current context.

        """
        if isinstance(self.definition.account_id, (int, six.string_types)):
            return str(self.definition.account_id)
        if isinstance(self.definition.account_id, dict):
            result = self.definition.account_id.get(self.ctx.env.name)
            if result:
                return str(result)
        return None

    @property
    def assume_role_config(self):
        # type: () -> Dict[str, Union[int, str]]
        """Parse the definition to get the correct assume role configuration.

        Returns:
            Dict[str, Union[int, str]]: Assume role definition for the current
            context.

        """
        assume_role = self.definition.assume_role
        if not assume_role:
            LOGGER.debug('assume_role not configured for deployment: %s',
                         self.name)
            return {}
        if isinstance(assume_role, dict):
            top_level = {
                'revert_on_exit': assume_role.get('post_deploy_env_revert',
                                                  False),
                'session_name': assume_role.get('session_name')
            }
            if assume_role.get('arn'):
                LOGGER.debug('role found in the top level dict: %s',
                             assume_role['arn'])
                return {
                    'role_arn': assume_role['arn'],
                    'duration_seconds': assume_role.get('duration'),
                    **top_level
                }
            if assume_role.get(self.ctx.env.name):
                env_assume_role = assume_role[self.ctx.env.name]
                if isinstance(env_assume_role, dict):
                    LOGGER.debug('role found in deploy environment dict: %s',
                                 env_assume_role['arn'])
                    return {
                        'role_arn': env_assume_role['arn'],
                        'duration_seconds': env_assume_role.get('duration'),
                        **top_level
                    }
                LOGGER.debug('role found for environment: %s', env_assume_role)
                return {'role_arn': env_assume_role, **top_level}
            LOGGER.info('Skipping iam:AssumeRole; no role found for deploy '
                        'environment "%s"...', self.ctx.env.name)
            return {}
        LOGGER.debug('role found: %s', assume_role)
        return {'role_arn': assume_role,
                'revert_on_exit': False}

    @cached_property
    def regions(self):
        # type: () -> List[str]
        """List of regions this deployment is associated with."""
        return self.definition.parallel_regions or self.definition.regions

    @cached_property
    def use_async(self):
        # type: () -> bool
        """Whether to use asynchronous method."""
        return bool(self.definition.parallel_regions and self.ctx.use_concurrent)

    def deploy(self):
        # type: () -> None
        """Deploy the deployment.

        High level method for running a deployment.

        """
        LOGGER.debug('attempting to deploy "%s" to region(s): %s',
                     self.ctx.env.name,
                     ', '.join(self.regions))
        if self.use_async:
            return self.__async('deploy')
        return self.__sync('deploy')

    def destroy(self):
        # type: () -> None
        """Destroy the deployment.

        High level method for running a deployment.

        """
        LOGGER.debug('attempting to destroy "%s" in regions(s): %s',
                     self.ctx.env.name,
                     ', '.join(self.regions))
        if self.use_async:
            return self.__async('destroy')
        return self.__sync('destroy')

    def run(self, action, region):
        # type: (str, str) -> None
        """Run a single deployment in a single region.

        Low level API access to run a deployment object.

        Args:
            action (str): Action to run (deploy, destroy, plan, etc.)
            region (str): AWS region to run in.

        """
        context = self.ctx.copy() if self.use_async else self.ctx
        context.command = action
        context.env.aws_region = region

        with aws.AssumeRole(context, **self.assume_role_config):
            self.definition.resolve(context, self._variables)
            self.validate_account_credentials()
            Module.run_list(action=action,
                            context=context,
                            deployment=self.definition,
                            future=self._future,
                            modules=self.definition.modules,
                            variables=self._variables)

    def validate_account_credentials(self):
        # type: () -> None
        """Exit if requested deployment account doesn't match credentials.

        Raises:
            SystemExit: AWS Account associated with the current credentials
                did not match the defined criteria.

        """
        account = aws.AccountDetails(self.ctx)
        if self.account_id_config:
            if self.account_id_config != account.id:
                LOGGER.error('Current AWS account "%s" does not match '
                             'required account "%s" in Runway config.',
                             account.id,
                             self.account_id_config)
                sys.exit(1)
            LOGGER.info('Verified current AWS account matches required '
                        'account id "%s".', self.account_id_config)
        if self.account_alias_config:
            if self.account_alias_config not in account.aliases:
                LOGGER.error('Current AWS account aliases "%s" do not match '
                             'required account alias "%s" in Runway config.',
                             ','.join(account.aliases),
                             self.account_alias_config)
                sys.exit(1)
            LOGGER.info('Verified current AWS account alias matches required '
                        'alias "%s".',
                        self.account_alias_config)

    def __merge_env_vars(self):
        # type: () -> None
        """Merge defined env_vars into context.env_vars."""
        if self.definition.env_vars:
            env_vars = merge_nested_environment_dicts(self.definition.env_vars,
                                                      env_name=self.ctx.env.name,
                                                      env_root=str(self.ctx.env.root_dir))
            if env_vars:
                LOGGER.info('OS environment variable overrides being applied '
                            'this deployment: %s', str(env_vars))
            self.ctx.env.vars = merge_dicts(self.ctx.env.vars, env_vars)

    def __async(self, action):
        # type: (str) -> None
        """Execute asynchronously.

        Args:
            action (str): Name of action to run.

        """
        LOGGER.info('Processing regions in parallel... '
                    '(output will be interwoven)')
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.ctx.env.max_concurrent_regions
        )
        futures = [executor.submit(self.run, *[action, region])
                   for region in self.regions]
        concurrent.futures.wait(futures)
        for job in futures:
            job.result()  # raise exceptions / exit as needed

    def __sync(self, action):
        # type: (str) -> None
        """Execute synchronously.

        Args:
            action (str): Name of action to run.

        """
        LOGGER.info('Processing regions sequentially...')
        for region in self.regions:
            LOGGER.info("")
            LOGGER.info('====== Processing region %s ======',
                        region)
            self.run(action, region)

    @classmethod
    def run_list(cls,
                 action,  # type: str
                 context,  # type: Context
                 deployments,  # type: List[DeploymentDefinition]
                 future,  # type: FutureDefinition
                 variables  # type: VariablesDefinition
                 ):
        # type: (...) -> None
        """Run a list of deployments.

        Args:
            action (str): Name of action to run.
            context (Context): Runway context.
            deployments (List[DeploymentDefinition]): List of deployments to run.
            future (FutureDefinition): Future definition.
            variables (VariablesDefinition): Runway variables for lookup
                resolution.

        """
        for deployment in deployments:
            LOGGER.debug('Resolving deployment for preprocessing...')
            deployment.resolve(context, variables=variables, pre_process=True)
            LOGGER.info('')
            LOGGER.info('')
            LOGGER.info('====== Processing deployment "%s" ======',
                        deployment.name)
            if not deployment.modules:
                LOGGER.warning('No modules found for deployment "%s"',
                               deployment.name)
                continue
            cls(context=context,
                definition=deployment,
                future=future,
                variables=variables)[action]()

    def __getitem__(self, key):
        """Make the object subscriptable.

        Args:
            key (str): Attribute to get.

        Returns:
            Any

        """
        return getattr(self, key)
