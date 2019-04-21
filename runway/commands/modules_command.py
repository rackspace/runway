"""runway env module."""
from __future__ import print_function

# pylint trips up on this in virtualenv
# https://github.com/PyCQA/pylint/issues/73
from distutils.util import strtobool  # noqa pylint: disable=no-name-in-module,import-error

import copy
import glob
import logging
import os
import sys

from builtins import input

import boto3
import six
import yaml

from .runway_command import RunwayCommand, get_env
from ..context import Context
from ..util import (
    change_dir, load_object_from_string, merge_dicts,
    merge_nested_environment_dicts
)

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


def determine_module_class(path, class_path):
    """Determine type of module and return deployment module class."""
    if not class_path:
        # First check directory name for type-indicating suffix
        basename = os.path.basename(path)
        if basename.endswith('.sls'):
            class_path = 'runway.module.serverless.Serverless'
        elif basename.endswith('.tf'):
            class_path = 'runway.module.terraform.Terraform'
        elif basename.endswith('.cdk'):
            class_path = 'runway.module.cdk.CloudDevelopmentKit'
        elif basename.endswith('.cfn'):
            class_path = 'runway.module.cloudformation.CloudFormation'

    if not class_path:
        # Fallback to autodetection
        if os.path.isfile(os.path.join(path, 'serverless.yml')):
            class_path = 'runway.module.serverless.Serverless'
        elif glob.glob(os.path.join(path, '*.tf')):
            class_path = 'runway.module.terraform.Terraform'
        elif os.path.isfile(os.path.join(path, 'cdk.json')) \
                and os.path.isfile(os.path.join(path, 'package.json')):
            class_path = 'runway.module.cdk.CloudDevelopmentKit'
        elif glob.glob(os.path.join(path, '*.env')) or (
                glob.glob(os.path.join(path, '*.yaml'))) or (
                    glob.glob(os.path.join(path, '*.yml'))):
            class_path = 'runway.module.cloudformation.CloudFormation'

    if not class_path:
        LOGGER.error('No module class found for %s', os.path.basename(path))
        sys.exit(1)

    return load_object_from_string(class_path)


def path_is_current_dir(path):
    """Determine if defined path is reference to current directory."""
    if path in ['.', '.' + os.sep]:
        return True
    return False


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
            LOGGER.info('Skipping assume-role; no role found for '
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
    if isinstance(deployment.get('account-id'), (int, six.string_types)):
        account_id = str(deployment['account-id'])
    elif deployment.get('account-id', {}).get(context.env_name):
        account_id = str(deployment['account-id'][context.env_name])
    else:
        account_id = None
    if account_id:
        validate_account_id(boto3.client('sts', **boto_args), account_id)
    if isinstance(deployment.get('account-alias'), six.string_types):
        account_alias = deployment['account-alias']
    elif deployment.get('account-alias', {}).get(context.env_name):
        account_alias = deployment['account-alias'][context.env_name]
    else:
        account_alias = None
    if account_alias:
        validate_account_alias(boto3.client('iam', **boto_args),
                               account_alias)


def echo_detected_environment(env_name, env_vars):
    """Print a helper note about how the environment was determined."""
    env_override_name = 'DEPLOY_ENVIRONMENT'
    LOGGER.info("")
    if env_override_name in env_vars:
        LOGGER.info("Environment \"%s\" was determined from the %s environment variable.",
                    env_name,
                    env_override_name)
        LOGGER.info("If this is not correct, update "
                    "the value (or unset it to fall back to the name of "
                    "the current git branch or parent directory).")
    else:
        LOGGER.info("Environment \"%s\" was determined from the current "
                    "git branch or parent directory.",
                    env_name)
        LOGGER.info("If this is not the environment name, update the branch/folder name or "
                    "set an override value via the %s environment variable",
                    env_override_name)
    LOGGER.info("")


class ModulesCommand(RunwayCommand):
    """Env deployment class."""

    def run(self, deployments=None, command='plan'):  # noqa pylint: disable=too-many-branches,too-many-statements
        """Execute apps/code command."""
        if deployments is None:
            deployments = self.runway_config['deployments']
        context = Context(env_name=get_env(self.env_root,
                                           self.runway_config.get('ignore_git_branch', False)),
                          env_region=None,
                          env_root=self.env_root,
                          env_vars=os.environ.copy())
        echo_detected_environment(context.env_name, context.env_vars)

        # set default names if needed
        for i, deployment in enumerate(deployments):
            if not deployment.get('name'):
                deployment['name'] = 'deployment_' + str(i+1)

        if command == 'destroy':
            LOGGER.info('WARNING!')
            LOGGER.info('Runway is running in DESTROY mode.')

        if context.env_vars.get('CI', None):
            if command == 'destroy':
                deployments_to_run = self.reverse_deployments(deployments)
            else:
                deployments_to_run = deployments
        else:
            if command == 'destroy':
                LOGGER.info('Any/all deployment(s) selected will be '
                            'irrecoverably DESTROYED.')
                deployments_to_run = self.reverse_deployments(
                    self.select_deployment_to_run(
                        context.env_name,
                        deployments,
                        command=command
                    )
                )
            else:
                deployments_to_run = self.select_deployment_to_run(
                    context.env_name,
                    deployments
                )

        LOGGER.info("Found %d deployment(s)", len(deployments_to_run))
        for i, deployment in enumerate(deployments_to_run):
            LOGGER.info("")
            LOGGER.info("")
            LOGGER.info("======= Processing deployment '%s' ===========================",
                        deployment.get('name'))

            if deployment.get('regions'):
                if deployment.get('env_vars'):
                    deployment_env_vars = merge_nested_environment_dicts(
                        deployment.get('env_vars'), env_name=context.env_name,
                        env_root=self.env_root
                    )
                    if deployment_env_vars:
                        LOGGER.info("OS environment variable overrides being "
                                    "applied this deployment: %s",
                                    str(deployment_env_vars))
                    context.env_vars = merge_dicts(context.env_vars, deployment_env_vars)

                LOGGER.info("")
                LOGGER.info("Attempting to deploy '%s' to region(s): %s",
                            context.env_name,
                            ", ".join(deployment['regions']))

                for region in deployment['regions']:
                    LOGGER.info("")
                    LOGGER.info("======= Processing region %s ================"
                                "===========", region)

                    context.env_region = region
                    context.env_vars = merge_dicts(
                        context.env_vars,
                        {'AWS_DEFAULT_REGION': context.env_region,
                         'AWS_REGION': context.env_region}
                    )
                    if deployment.get('assume-role'):
                        pre_deploy_assume_role(deployment['assume-role'], context)
                    if deployment.get('account-id') or (deployment.get('account-alias')):
                        validate_account_credentials(deployment, context)

                    modules = deployment.get('modules', [])
                    if deployment.get('current_dir'):
                        modules.append('.' + os.sep)
                    for module in modules:
                        self._deploy_module(module, deployment, context, command)

                if deployment.get('assume-role'):
                    post_deploy_assume_role(deployment['assume-role'], context)
            else:
                LOGGER.error('No region configured for any deployment')
                sys.exit(1)

    def _deploy_module(self, module, deployment, context, command):
        module_opts = {}
        if deployment.get('environments'):
            module_opts['environments'] = deployment['environments'].copy()  # noqa
        if deployment.get('module_options'):
            module_opts['options'] = deployment['module_options'].copy()  # noqa
        if isinstance(module, six.string_types):
            module = {'path': module}
        if path_is_current_dir(module['path']):
            module_root = self.env_root
        else:
            module_root = os.path.join(self.env_root, module['path'])
        module_opts = merge_dicts(module_opts, module)
        module_opts = load_module_opts_from_file(module_root, module_opts)
        if deployment.get('skip-npm-ci'):
            module_opts['skip_npm_ci'] = True

        LOGGER.info("")
        LOGGER.info("---- Processing module '%s' for '%s' in %s --------------",
                    module['path'],
                    context.env_name,
                    context.env_region)
        LOGGER.info("Module options: %s", module_opts)
        with change_dir(module_root):
            # dynamically load the particular module's class, 'get' the method
            # associated with the command, and call the method
            module_class = determine_module_class(module_root,
                                                  module_opts.get('class_path'))
            module_instance = module_class(
                context=context,
                path=module_root,
                options=module_opts
            )
            if hasattr(module_instance, command):
                command_method = getattr(module_instance, command)
                command_method()
            else:
                LOGGER.error("'%s' is missing method '%s'",
                             module_instance, command)
                sys.exit(1)

    @staticmethod
    def reverse_deployments(deployments=None):
        """Reverse deployments and the modules/regions in them."""
        if deployments is None:
            deployments = []

        reversed_deployments = []
        for i in deployments[::-1]:
            deployment = copy.deepcopy(i)
            for config in ['modules', 'regions']:
                if deployment.get(config):
                    deployment[config] = deployment[config][::-1]
            reversed_deployments.append(deployment)
        return reversed_deployments

    @staticmethod
    def select_deployment_to_run(env_name, deployments=None, command='build'):  # noqa pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Query user for deployments to run."""
        if deployments is None or not deployments:
            return []
        deployments_to_run = []

        num_deployments = len(deployments)

        if num_deployments == 1:
            selected_deployment_index = 1
        else:
            print('')
            print('Configured deployments:')
            for i, deployment in enumerate(deployments):
                print(" %d: %s" % (i+1, _deployment_menu_entry(deployment)))
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
        if selected_deployment.get('current_dir', False):
            deployments_to_run.append(selected_deployment)
        elif not selected_deployment.get('modules', []):
            LOGGER.error('No modules configured in selected deployment')
            sys.exit(1)
        elif len(selected_deployment['modules']) == 1:
            # No need to select a module in the deployment - there's only one
            if command == 'destroy':
                LOGGER.info('(only one deployment detected; all modules '
                            'automatically selected for termination)')
                if not strtobool(input('Proceed?: ')):
                    sys.exit(0)
            deployments_to_run.append(selected_deployment)
        else:
            modules = selected_deployment['modules']
            print('')
            print('Configured modules in deployment \'%s\':' % selected_deployment.get('name'))
            for i, module in enumerate(modules):
                print(" %s: %s" % (i+1, _module_menu_entry(module, env_name)))
            print('')
            print('')
            if command == 'destroy':
                print('(Operating in destroy mode -- "all" will destroy all '
                      'deployments in reverse order)')
            selected_module_index = input('Enter number of module to run (or "all"): ')
            if selected_module_index == 'all':
                deployments_to_run.append(selected_deployment)
            elif selected_module_index == '' or (
                    not selected_module_index.isdigit() or (
                        not 0 < int(selected_module_index) <= len(modules))):
                LOGGER.error('Please select a valid number (or "all")')
                sys.exit(1)
            else:
                selected_deployment['modules'] = [modules[int(selected_module_index) - 1]]
                deployments_to_run.append(selected_deployment)

        LOGGER.debug('Selected deployment is %s...', deployments_to_run)
        return deployments_to_run


def _module_name_for_display(module):
    """Extract a name for the module."""
    if isinstance(module, dict):
        return module['path']
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
