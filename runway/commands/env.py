"""runway env module."""
from __future__ import print_function

# pylint trips up on this in virtualenv
# https://github.com/PyCQA/pylint/issues/73
from distutils.util import strtobool  # noqa pylint: disable=no-name-in-module,import-error

from subprocess import check_call, check_output

import copy
import glob
import json
import logging
import os
import shutil
import sys

from builtins import input

import boto3
import six
import yaml

from .base import Base
from ..context import Context
from ..util import change_dir, load_object_from_string, merge_dicts

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


def determine_module_class(path, module_options):
    """Determine type of module and return deployment module class."""
    if not module_options.get('class_path'):
        # First check directory name for type-indicating suffix
        if os.path.basename(path).endswith('.sls'):
            module_options['class_path'] = 'runway.module.serverless.Serverless'  # noqa
        elif os.path.basename(path).endswith('.tf'):
            module_options['class_path'] = 'runway.module.terraform.Terraform'  # noqa
        elif os.path.basename(path).endswith('.cfn'):
            module_options['class_path'] = 'runway.module.cloudformation.CloudFormation'  # noqa
        # Fallback to autodetection
        elif os.path.isfile(os.path.join(path,
                                         'serverless.yml')):
            module_options['class_path'] = 'runway.module.serverless.Serverless'  # noqa
        elif glob.glob(os.path.join(path, '*.tf')):
            module_options['class_path'] = 'runway.module.terraform.Terraform'  # noqa
        elif glob.glob(os.path.join(path, '*.env')):
            module_options['class_path'] = 'runway.module.cloudformation.CloudFormation'  # noqa
    if not module_options.get('class_path'):
        LOGGER.error('No valid deployment configurations found for %s',
                     os.path.basename(path))
        sys.exit(1)
    return load_object_from_string(module_options['class_path'])


def get_env_from_branch(branch_name):
    """Determine environment name from git branch name."""
    if branch_name.startswith('ENV-'):
        return branch_name[4:]
    if branch_name == 'master':
        LOGGER.info('Translating git branch "master" to environment '
                    '"common"')
        return 'common'
    return branch_name


def get_env_from_directory(directory_name):
    """Determine environment name from directory name."""
    if directory_name.startswith('ENV-'):
        return directory_name[4:]
    return directory_name


def get_env(path, ignore_git_branch=False):
    """Determine environment name."""
    if 'DEPLOY_ENVIRONMENT' in os.environ:
        return os.environ['DEPLOY_ENVIRONMENT']

    if ignore_git_branch:
        LOGGER.info('Skipping environment lookup from current git branch '
                    '("ignore_git_branch" is set to true in the runway '
                    'config)')
    else:
        # These are not located with the top imports because they throw an
        # error if git isn't installed
        from git import Repo as GitRepo
        from git.exc import InvalidGitRepositoryError

        try:
            b_name = GitRepo(
                path,
                search_parent_directories=True
            ).active_branch.name
            LOGGER.info('Deriving environment name from git branch %s...',
                        b_name)
            return get_env_from_branch(b_name)
        except InvalidGitRepositoryError:
            pass
    LOGGER.info('Deriving environment name from directory %s...', path)
    return get_env_from_directory(os.path.basename(path))


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


class Env(Base):
    """Env deployment class."""

    def gitclean(self):
        """Execute git clean to remove untracked/build files."""
        clean_cmd = ['git', 'clean', '-X', '-d']
        if 'CI' not in os.environ:
            print('The following files/directories will be deleted:')
            print('')
            print(check_output(clean_cmd + ['-n']).decode())
            if not strtobool(input('Proceed?: ')):
                return False
        check_call(clean_cmd + ['-f'])
        empty_dirs = self.get_empty_dirs(self.env_root)
        if empty_dirs != []:
            print('Now removing empty directories:')
        for directory in empty_dirs:
            print("Removing %s/" % directory)
            shutil.rmtree(os.path.join(self.env_root, directory))
        return True

    def run(self, deployments=None, command='plan'):  # noqa pylint: disable=too-many-branches
        """Execute apps/code command."""
        if deployments is None:
            deployments = self.runway_config['deployments']
        context = Context(options=self.options,
                          env_name=get_env(
                              self.env_root,
                              self.runway_config.get('ignore_git_branch',
                                                     False)
                          ),
                          env_region=None,
                          env_root=self.env_root,
                          env_vars=os.environ.copy())
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
                        deployments,
                        command=command
                    )
                )
            else:
                deployments_to_run = self.select_deployment_to_run(
                    deployments
                )
        for deployment in deployments_to_run:
            if deployment.get('regions'):
                for region in deployment['regions']:
                    context.env_region = region
                    context.env_vars = merge_dicts(
                        context.env_vars,
                        {'AWS_DEFAULT_REGION': context.env_region,
                         'AWS_REGION': context.env_region}
                    )
                    if deployment.get('assume-role'):
                        pre_deploy_assume_role(deployment['assume-role'],
                                               context)
                    if deployment.get('account-id') or (
                            deployment.get('account-alias')):
                        validate_account_credentials(deployment, context)
                    modules = deployment.get('modules', [])
                    if deployment.get('current_dir'):
                        modules.append('.' + os.sep)
                    for module in modules:
                        module_opts = {}
                        if deployment.get('environments'):
                            module_opts['environments'] = deployment['environments'].copy()  # noqa
                        if isinstance(module, six.string_types):
                            module = {'path': module}
                        if path_is_current_dir(module['path']):
                            module_root = self.env_root
                        else:
                            module_root = os.path.join(self.env_root,
                                                       module['path'])
                        module_opts = merge_dicts(module_opts, module)
                        module_opts = load_module_opts_from_file(module_root,
                                                                 module_opts)
                        if deployment.get('skip-npm-ci'):
                            module_opts['skip_npm_ci'] = True
                        with change_dir(module_root):
                            getattr(
                                determine_module_class(module_root, module_opts)(  # noqa
                                    context=context,
                                    path=module_root,
                                    options=module_opts
                                ),
                                command)()
                if deployment.get('assume-role'):
                    post_deploy_assume_role(deployment['assume-role'], context)

    def plan(self, deployments=None):
        """Plan apps/code deployment."""
        self.run(deployments=deployments, command='plan')

    def deploy(self, deployments=None):
        """Deploy apps/code."""
        self.run(deployments=deployments, command='deploy')

    def destroy(self, deployments=None):
        """Deploy apps/code."""
        self.run(deployments=deployments, command='destroy')

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
    def select_deployment_to_run(deployments=None, command='build'):  # noqa pylint: disable=too-many-branches,too-many-statements
        """Query user for deployments to run."""
        if deployments is None or not deployments:
            return []
        deployments_to_run = []

        if len(deployments) == 1:
            selected_index = 1
        else:
            print('')
            print('Configured deployments:')
            pretty_index = 1
            for i in deployments:
                print("%s: %s" % (pretty_index, json.dumps(i)))
                pretty_index += 1
            print('')
            print('')
            if command == 'destroy':
                print('(Operating in destroy mode -- "all" will destroy all '
                      'deployments in reverse order)')
            selected_index = input('Enter number of deployment to run '
                                   '(or "all"): ')

        if selected_index == 'all':
            return deployments
        if selected_index == '':
            LOGGER.error('Please select a valid number (or "all")')
            sys.exit(1)

        selected_deploy = deployments[int(selected_index) - 1]
        if selected_deploy.get('current_dir', False):
            deployments_to_run.append(selected_deploy)
        elif not selected_deploy.get('modules', []):
            LOGGER.error('No modules configured in selected deployment')
            sys.exit(1)
        elif len(selected_deploy['modules']) == 1:
            # No need to select a module in the deployment - there's only one
            if command == 'destroy':
                LOGGER.info('(only one deployment detected; all modules '
                            'automatically selected for termination)')
                if not strtobool(input('Proceed?: ')):
                    sys.exit(0)
            deployments_to_run.append(selected_deploy)
        else:
            print('')
            print('Configured modules in deployment:')
            pretty_index = 1
            for i in selected_deploy['modules']:
                print("%s: %s" % (pretty_index, json.dumps(i)))
                pretty_index += 1
            print('')
            print('')
            if command == 'destroy':
                print('(Operating in destroy mode -- "all" will destroy all '
                      'deployments in reverse order)')
            selected_index = input('Enter number of module to run '
                                   '(or "all"): ')
            if selected_index == 'all':
                deployments_to_run.append(selected_deploy)
            elif selected_index == '':
                LOGGER.error('Please select a valid number (or "all")')
                sys.exit(1)
            else:
                module_list = [selected_deploy['modules'][int(selected_index) - 1]]  # noqa
                selected_deploy['modules'] = module_list
                deployments_to_run.append(selected_deploy)

        LOGGER.debug('Selected deployment is %s...', deployments_to_run)
        return deployments_to_run
