"""Runway env module."""
from __future__ import print_function

# pylint trips up on this in virtualenv
# https://github.com/PyCQA/pylint/issues/73
from distutils.util import strtobool  # noqa pylint: disable=no-name-in-module,import-error

import copy
import logging
import os
import sys

from builtins import input

import boto3
import six
import yaml

from .runway_command import RunwayCommand, get_env
from ..context import Context
from ..path import Path
from ..runway_module_type import RunwayModuleType
from ..util import (change_dir, extract_boto_args_from_env, merge_dicts,
                    merge_nested_environment_dicts)

if sys.version_info[0] > 2:
    import concurrent.futures

LOGGER = logging.getLogger('runway')


def assume_role(role_arn, session_name=None, duration_seconds=None,
                region='us-east-1', env_vars=None):
    """Assume IAM role."""
    if session_name is None:
        session_name = 'runway'
    assume_role_opts = {'RoleArn': role_arn,
                        'RoleSessionName': session_name}
    if duration_seconds:
        assume_role_opts['DurationSeconds'] = int(duration_seconds)
    boto_args = {}
    if env_vars:
        for i in ['aws_access_key_id', 'aws_secret_access_key',
                  'aws_session_token']:
            if env_vars.get(i.upper()):
                boto_args[i] = env_vars[i.upper()]

    sts_client = boto3.client('sts', region_name=region, **boto_args)
    LOGGER.info("Assuming role %s...", role_arn)
    response = sts_client.assume_role(**assume_role_opts)
    return {'AWS_ACCESS_KEY_ID': response['Credentials']['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': response['Credentials']['SecretAccessKey'],  # noqa
            'AWS_SESSION_TOKEN': response['Credentials']['SessionToken']}


def load_module_opts_from_file(path, module_options):
    """Update module_options with any options defined in module path."""
    module_options_file = os.path.join(path,
                                       'runway.module.yml')
    if os.path.isfile(module_options_file):
        with open(module_options_file, 'r') as stream:
            module_options = merge_dicts(module_options,
                                         yaml.safe_load(stream))
    return module_options


def post_deploy_assume_role(assume_role_config, context):
    """Revert to previous credentials, if necessary."""
    if isinstance(assume_role_config, dict):
        if assume_role_config.get('post_deploy_env_revert'):
            context.restore_existing_iam_env_vars()


def pre_deploy_assume_role(assume_role_config, context):
    """Assume role (prior to deployment)."""
    if isinstance(assume_role_config, dict):
        assume_role_arn = ''
        if assume_role_config.get('post_deploy_env_revert'):
            context.save_existing_iam_env_vars()
        if assume_role_config.get('arn'):
            assume_role_arn = assume_role_config['arn']
            assume_role_duration = assume_role_config.get('duration')
        elif assume_role_config.get(context.env_name):
            if isinstance(assume_role_config[context.env_name], dict):
                assume_role_arn = assume_role_config[context.env_name]['arn']  # noqa
                assume_role_duration = assume_role_config[context.env_name].get('duration')  # noqa pylint: disable=line-too-long
            else:
                assume_role_arn = assume_role_config[context.env_name]
                assume_role_duration = None
        else:
            LOGGER.info('Skipping iam:AssumeRole; no role found for '
                        'environment %s...',
                        context.env_name)

        if assume_role_arn:
            context.env_vars = merge_dicts(
                context.env_vars,
                assume_role(
                    role_arn=assume_role_arn,
                    session_name=assume_role_config.get('session_name', None),
                    duration_seconds=assume_role_duration,
                    region=context.env_region,
                    env_vars=context.env_vars
                )
            )
    else:
        context.env_vars = merge_dicts(
            context.env_vars,
            assume_role(role_arn=assume_role_config,
                        region=context.env_region,
                        env_vars=context.env_vars)
        )


def select_modules_to_run(deployment, tags, command=None,  # noqa pylint: disable=too-many-branches,invalid-name
                          ci=False, env_name=None):
    """Select modules to run based on tags.

    Args:
        deployment (Dict[str, Any): A deployment definition.
        tags (Optional[List[str]]): List of required tags that must
            exist on a module for it to be returned.
        command (str): Command used to initiate this process.
        ci (Optional[str]): Value of CI environment variable.
        env_name (Optional[str]): Name of environment being processed.

    Returns:
        Deployment with filtered modules.

    """
    if ci and not tags:
        return deployment
    modules_to_deploy = []

    if not deployment.get('modules'):
        LOGGER.error('No modules configured in deployment "%s"',
                     deployment['name'])
        sys.exit(1)
    if len(deployment['modules']) == 1 and not tags:
        # No need to select a module in the deployment - there's only one
        if command == 'destroy':
            LOGGER.info('(only one deployment detected; all modules '
                        'automatically selected for termination)')
            if not ci:
                if not strtobool(input('Proceed?: ')):
                    sys.exit(0)
        return deployment

    modules = deployment['modules']

    if not tags and not ci:
        print('')
        print('Configured modules in deployment \'%s\':' % deployment.get('name'))
        for i, module in enumerate(modules):
            print(" %s: %s" % (i + 1, _module_menu_entry(module, env_name)))
        print('')
        print('')
        if command == 'destroy':
            print('(Operating in destroy mode -- "all" will destroy all '
                  'deployments in reverse order)')
        selected_module_index = input('Enter number of module to run (or "all"): ')
        if selected_module_index == 'all':
            return deployment
        if selected_module_index == '' or (
                not selected_module_index.isdigit() or (
                    not 0 < int(selected_module_index) <= len(modules))):
            LOGGER.error('Please select a valid number (or "all")')
            sys.exit(1)
        deployment['modules'] = [modules[int(selected_module_index) - 1]]
        if deployment['modules'][0].get('child_modules'):
            # Allow user to select individual module out of list of child
            # modules that can be run in parallel
            deployment['modules'] = deployment['modules'][0].get('child_modules')
            deployment['name'] = deployment['name'] + '_parallel_modules_' + selected_module_index
            deployment = select_modules_to_run(deployment,
                                               tags,
                                               command,
                                               ci,
                                               env_name)
        return deployment

    for module in modules:
        if isinstance(module, str):
            LOGGER.warning('Module "%s.%s" is defined as a string '
                           'which cannot be used with the "--tag" '
                           'option so it has been skipped. Please '
                           'update this module definition to a dict '
                           'to use "--tag".', deployment['name'],
                           module)
            continue  # this doesn't need to return an error
        if module.get('child_modules'):
            module['child_modules'] = [x for x in module['child_modules']
                                       if x.get('tags') and all(i in x['tags'] for i in tags)]
            if module.get('child_modules'):
                modules_to_deploy.append(module)
        elif module.get('tags') and all(i in module['tags'] for i in tags):
            modules_to_deploy.append(module)
    deployment['modules'] = modules_to_deploy
    return deployment


def validate_account_alias(iam_client, account_alias):
    """Exit if list_account_aliases doesn't include account_alias."""
    # Super overkill here using pagination when an account can only
    # have a single alias, but at least this implementation should be
    # future-proof
    current_account_aliases = []
    paginator = iam_client.get_paginator('list_account_aliases')
    response_iterator = paginator.paginate()
    for page in response_iterator:
        current_account_aliases.extend(page.get('AccountAliases', []))
    if account_alias in current_account_aliases:
        LOGGER.info('Verified current AWS account alias matches required '
                    'alias %s.',
                    account_alias)
    else:
        LOGGER.error('Current AWS account aliases "%s" do not match '
                     'required account alias %s in Runway config.',
                     ','.join(current_account_aliases),
                     account_alias)
        sys.exit(1)


def validate_account_id(sts_client, account_id):
    """Exit if get_caller_identity doesn't match account_id."""
    resp = sts_client.get_caller_identity()
    if 'Account' in resp:
        if resp['Account'] == account_id:
            LOGGER.info('Verified current AWS account matches required '
                        'account id %s.',
                        account_id)
        else:
            LOGGER.error('Current AWS account %s does not match '
                         'required account %s in Runway config.',
                         resp['Account'],
                         account_id)
            sys.exit(1)
    else:
        LOGGER.error('Error checking current account ID')
        sys.exit(1)


def validate_account_credentials(deployment, context):
    """Exit if requested deployment account doesn't match credentials."""
    boto_args = {'region_name': context.env_vars['AWS_DEFAULT_REGION']}
    for i in ['aws_access_key_id', 'aws_secret_access_key',
              'aws_session_token']:
        if context.env_vars.get(i.upper()):
            boto_args[i] = context.env_vars[i.upper()]
    if isinstance(deployment.get('account_id'), (int, six.string_types)):
        account_id = str(deployment['account_id'])
    elif deployment.get('account_id', {}).get(context.env_name):
        account_id = str(deployment['account_id'][context.env_name])
    else:
        account_id = None
    if account_id:
        validate_account_id(boto3.client('sts', **boto_args), account_id)
    if isinstance(deployment.get('account_alias'), six.string_types):
        account_alias = deployment['account_alias']
    elif deployment.get('account_alias', {}).get(context.env_name):
        account_alias = deployment['account_alias'][context.env_name]
    else:
        account_alias = None
    if account_alias:
        validate_account_alias(boto3.client('iam', **boto_args),
                               account_alias)


def validate_environment(module_name, env_def, env_vars):
    """Check if an environment should be deployed to.

    Args:
        module_name (str): Name of the module being validated.
        env_def (Union[bool, str, List[str]]): Environment definition from
            the config file. Can be bool, string of "$ACCOUNT_ID/$REGION",
            or a list of strings.
        env_vars (Dict[str, str]): Environment variables.

    Returns:
        Booleon value of wether to deploy or not.

    """
    if isinstance(env_def, bool):  # explicit enable or disable
        if env_def:
            LOGGER.debug('Module \'%s\' explicitly enabled', module_name)
            return True

        LOGGER.info('')
        LOGGER.info(
            '---- Skipping module \'%s\'; explicitly disabled ----------',
            module_name
        )
        return False

    if isinstance(env_def, (list, six.string_types)):
        boto_args = extract_boto_args_from_env(env_vars)
        sts_client = boto3.client('sts', **boto_args)
        current_env = '{}/{}'.format(
            sts_client.get_caller_identity()['Account'],
            env_vars['AWS_DEFAULT_REGION']
        )

        if current_env in env_def:
            LOGGER.debug('Current environment \'%s\' found in %s for module \'%s\'',
                         current_env, str(env_def), module_name)
            return True
        LOGGER.info('')
        LOGGER.info(
            '---- Skipping module \'%s\'; account_id/region mismatch ---',
            module_name
        )
        return False
    raise TypeError('env_def of type "%s" provided to validate_environment; '
                    'expected type of bool, list, or str' % type(env_def))


class ModulesCommand(RunwayCommand):
    """Env deployment class."""

    def run(self, deployments=None, command='plan'):
        """Execute apps/code command."""
        if deployments is None:
            deployments = self.runway_config['deployments']
        context = Context(env_name=get_env(self.env_root,
                                           self.runway_config.ignore_git_branch,
                                           prompt_if_unexpected=bool(not os.getenv('CI'))),
                          env_region=None,
                          env_root=self.env_root,
                          env_vars=os.environ.copy(),
                          command=command)
        context.env_vars['RUNWAYCONFIG'] = self.runway_config_path

        # set default names if needed
        for i, deployment in enumerate(deployments):
            if not deployment.get('name'):
                deployment['name'] = 'deployment_' + str(i + 1)

        if command == 'destroy':
            LOGGER.info('WARNING!')
            LOGGER.info('Runway is running in DESTROY mode.')
            LOGGER.info('Any/all deployment(s) selected will be '
                        'irrecoverably DESTROYED.')
            if context.is_interactive:
                if not strtobool(input('Proceed?: ')):
                    sys.exit(0)

        if context.is_noninteractive or self._cli_arguments.get('--tag'):
            selected_deployments = deployments
        else:
            selected_deployments = self.select_deployment_to_run(
                deployments, command
            )

        deployments_to_run = [
            select_modules_to_run(deployment,
                                  self._cli_arguments.get('--tag'),
                                  command,
                                  context.is_noninteractive,
                                  context.env_name)
            for deployment in selected_deployments
        ]

        if command == 'destroy':
            deployments_to_run = self.reverse_deployments(
                deployments_to_run
            )

        LOGGER.info("")
        LOGGER.info("Found %d deployment(s)", len(deployments_to_run))

        self._process_deployments(deployments_to_run, context)

    def execute(self):
        # type: () -> None
        """Execute the command."""
        raise NotImplementedError('execute must be implimented for '
                                  'subclasses of BaseCommand.')

    def _process_deployments(self, deployments, context):
        """Process deployments."""
        for _, deployment in enumerate(deployments):
            LOGGER.debug('Resolving deployment for preprocessing...')
            deployment.resolve(context, self.runway_vars, pre_process=True)
            LOGGER.info("")
            LOGGER.info("")
            LOGGER.info("======= Processing deployment '%s' ===========================",
                        deployment.name)

            # a deployment with no modules is possible here - check before processing
            if not deployment.modules:
                LOGGER.warning('No modules found for deployment "%s"',
                               deployment.name)
                if self._cli_arguments.get('--tag'):
                    # added info about what could have caused the module to not be found
                    LOGGER.warning('Missing modules could be caused by an '
                                   'invalid value passed to the "--tag" '
                                   'argument: %s', str(self._cli_arguments['--tag']))
                # this is not necessarily a cause for concern so continue
                # to the next deployment rather than exiting
                continue

            if deployment.regions or deployment.parallel_regions:
                if deployment.env_vars:
                    deployment_env_vars = merge_nested_environment_dicts(
                        deployment.env_vars, env_name=context.env_name,
                        env_root=self.env_root
                    )
                    if deployment_env_vars:
                        LOGGER.info("OS environment variable overrides being "
                                    "applied this deployment: %s",
                                    str(deployment_env_vars))
                    context.env_vars = merge_dicts(context.env_vars,
                                                   deployment_env_vars)

                LOGGER.info("")

                if deployment.parallel_regions and context.use_concurrent:
                    LOGGER.info("Processing parallel regions %s",
                                deployment.parallel_regions)
                    LOGGER.info('(output will be interwoven)')
                    executor = concurrent.futures.ProcessPoolExecutor(
                        max_workers=context.max_concurrent_regions
                    )
                    futures = [executor.submit(self._execute_deployment,
                                               *[deployment, context,
                                                 region, True])
                               for region in deployment.parallel_regions]
                    concurrent.futures.wait(futures)
                    for job in futures:
                        job.result()  # Raise exceptions / exit as needed
                    continue

                # single var to reduce comparisons
                regions = deployment.parallel_regions or deployment.regions

                if deployment.parallel_regions:
                    LOGGER.info(
                        '%s - processing the regions sequentially...',
                        ('Not running in CI mode' if context.is_python3
                         else 'Parallel execution requires Python 3+')
                    )

                LOGGER.info("Attempting to deploy '%s' to region(s): %s",
                            context.env_name,
                            ", ".join(regions))

                for region in regions:
                    LOGGER.info("")
                    LOGGER.info("======= Processing region %s ================"
                                "===========", region)

                    self._execute_deployment(deployment, context, region)
            else:
                LOGGER.error('No region configured for any deployment')
                sys.exit(1)

    def _execute_deployment(self, deployment, context, region,
                            is_parallel_regions=False):
        """Execute a single deployment."""
        # this is going to invalidate the use post_deploy_assume_role
        # since assumed roles will never remain in the active context
        if is_parallel_regions:
            context = copy.deepcopy(context)  # in case of parallel regions

        context.env_region = region
        context.env_vars.update({'AWS_DEFAULT_REGION': region,
                                 'AWS_REGION': region})

        if deployment.assume_role:
            pre_deploy_assume_role(deployment.assume_role, context)
        if deployment.account_id or deployment.account_alias:
            validate_account_credentials(deployment, context)

        self._process_modules(deployment, context)

        if deployment.assume_role:
            post_deploy_assume_role(deployment.assume_role, context)

    def _process_modules(self, deployment, context):
        """Process the modules of a deployment."""
        for module in deployment.modules:
            if module.child_modules:
                if context.use_concurrent:
                    LOGGER.info("Processing parallel modules %s",
                                [x.path for x in module.child_modules])
                    LOGGER.info('(output will be interwoven)')
                    # Can't use threading or ThreadPoolExecutor here because
                    # we need to be able to do things like `cd` which is not
                    # thread safe.
                    executor = concurrent.futures.ProcessPoolExecutor(
                        max_workers=context.max_concurrent_modules
                    )
                    futures = [executor.submit(self._deploy_module,
                                               *[x, deployment, context])
                               for x in module.child_modules]
                    concurrent.futures.wait(futures)
                    for job in futures:
                        job.result()  # Raise exceptions / exit as needed
                else:
                    LOGGER.info(
                        '%s - processing the following '
                        'parallel modules sequentially...',
                        ('Not running in CI mode' if context.is_python3
                         else 'Parallel execution requires Python 3+')
                    )
                    for child_module in module.child_modules:
                        self._deploy_module(child_module,
                                            deployment,
                                            context)
            else:
                self._deploy_module(module, deployment, context)

    def _deploy_module(self, module, deployment, context):
        """Execute module deployment.

        1. Resolves variables in :class:`runway.config.DeploymentDefinition`
           and :class:`runway.config.ModuleDefinition`.
        2. Constructs a ``Dict`` of options to be passed to the ``module_class``.
        3. Determine the class to use to execute the
           :class:`runway.config.ModuleDefinition`, ``cd`` to the module
           directory, and instanteate the class.
        4. Find and execute the command method of the instanteated class.

        Args:
            module (:class:`runway.config.ModuleDefinition`): The module
                to be deployed.
            deployment (:class:`runway.config.DeploymentDefinition`): The
                deployment the module belongs to. Used to get options,
                environments, parameters, and env_vars from the deployment level.
            context: (:class:`runway.context.Context`): Current context instance.

        """
        deployment.resolve(context, self.runway_vars)
        module.resolve(context, self.runway_vars)
        module_opts = {
            'environments': deployment.environments.copy(),
            'options': deployment.module_options.copy(),
            'parameters': deployment.parameters.copy()
        }

        path = Path(module, self.env_root, os.path.join(self.env_root, '.runway_cache'))

        module_opts = merge_dicts(module_opts, module.data)
        module_opts = load_module_opts_from_file(path.module_root, module_opts)

        module_opts['environment'] = module_opts['environments'].get(
            context.env_name, {}
        )
        if isinstance(module_opts['environment'], dict):  # legacy support
            module_opts['parameters'].update(module_opts['environment'])
            if module_opts['parameters']:
                # deploy if env is empty but params are provided
                module_opts['environment'] = True
        else:
            if not validate_environment(module.name,
                                        module_opts['environment'],
                                        context.env_vars):
                return  # skip if env validation fails
            module_opts['environment'] = True

        LOGGER.info("")
        LOGGER.info("---- Processing module '%s' for '%s' in %s --------------",
                    module.path,
                    context.env_name,
                    context.env_region)
        LOGGER.info("Module options: %s", module_opts)
        if module_opts.get('env_vars'):
            module_env_vars = merge_nested_environment_dicts(
                module_opts.get('env_vars'), env_name=context.env_name,
                env_root=self.env_root
            )
            if module_env_vars:
                context = copy.deepcopy(context)  # changes for this mod only
                LOGGER.info("OS environment variable overrides being "
                            "applied to this module: %s",
                            str(module_env_vars))
                context.env_vars = merge_dicts(context.env_vars, module_env_vars)

        with change_dir(path.module_root):

            runway_module_type = RunwayModuleType(path.module_root,
                                                  module_opts.get('class_path'),
                                                  module_opts.get('type'))

            # dynamically load the particular module's class, 'get' the method
            # associated with the command, and call the method
            module_instance = runway_module_type.module_class(
                context=context,
                path=path.module_root,
                options=module_opts
            )
            if hasattr(module_instance, context.command):
                command_method = getattr(module_instance, context.command)
                command_method()
            else:
                LOGGER.error("'%s' is missing method '%s'",
                             module_instance, context.command)
                sys.exit(1)

    @staticmethod
    def reverse_deployments(deployments=None):
        """Reverse deployments and the modules/regions in them."""
        if deployments is None:
            deployments = []

        for deployment in deployments:
            deployment.reverse()

        deployments.reverse()
        return deployments

    @staticmethod
    def select_deployment_to_run(deployments=None, command='build'):
        """Query user for deployments to run."""
        if deployments is None or not deployments:
            return []

        num_deployments = len(deployments)

        if num_deployments == 1:
            selected_deployment_index = 1
        else:
            print('')
            print('Configured deployments:')
            for i, deployment in enumerate(deployments):
                print(" %d: %s" % (i + 1, _deployment_menu_entry(deployment)))
            print('')
            print('')
            if command == 'destroy':
                print('(Operating in destroy mode -- "all" will destroy all '
                      'deployments in reverse order)')
            selected_deployment_index = input('Enter number of deployment to run (or "all"): ')

        if selected_deployment_index == 'all':
            return deployments
        if selected_deployment_index == '':
            LOGGER.error('Please select a valid number (or "all")')
            sys.exit(1)

        selected_deployment = deployments[int(selected_deployment_index) - 1]

        LOGGER.debug('Selected deployment is %s...', selected_deployment)

        return [selected_deployment]


def _module_name_for_display(module):
    """Extract a name for the module."""
    if isinstance(module, dict):
        return module['path']
    try:
        return module.path
    except Exception:  # pylint: disable=broad-except
        return str(module)


def _module_menu_entry(module, environment_name):
    """Build a string to display in the 'select module' menu."""
    name = _module_name_for_display(module)
    if isinstance(module, dict):
        environment_config = module.get('environments', {}).get(environment_name)
        if environment_config:
            return "%s (%s)" % (name, environment_config)
    return "%s" % (name)


def _deployment_menu_entry(deployment):
    """Build a string to display in the 'select deployment' menu."""
    paths = ", ".join([_module_name_for_display(module) for module in deployment['modules']])
    regions = ", ".join(deployment.get('regions', []))
    return "%s - %s (%s)" % (deployment.get('name'), paths, regions)
