"""runway env module."""
from __future__ import print_function

# pylint trips up on this in virtualenv
# https://github.com/PyCQA/pylint/issues/73
from distutils.util import strtobool  # noqa pylint: disable=no-name-in-module,import-error

from subprocess import check_call, check_output

import copy
import json
import logging
import os
import shutil
import sys

from builtins import input  # pylint: disable=redefined-builtin

import boto3

from .base import Base
from .module import Module

LOGGER = logging.getLogger('runway')


class Env(Base):
    """Env deployment class."""

    def gitclean(self):
        """Execute git clean to remove untracked/build files."""
        clean_cmd = ['git', 'clean', '-X', '-d']
        if 'CI' not in self.env_vars:
            print('The following files/directories will be deleted:')
            print('')
            print(check_output(clean_cmd + ['-n']))
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
        if command == 'destroy':
            LOGGER.info('WARNING!')
            LOGGER.info('Runway is running in DESTROY mode.')
        if self.env_vars.get('CI', None):
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
                    if deployment.get('assume-role'):
                        self.pre_deploy_assume_role(deployment['assume-role'],
                                                    region)
                    self.update_env_vars({'AWS_DEFAULT_REGION': region,
                                          'AWS_REGION': region})
                    if deployment.get('account-id') or (
                            deployment.get('account-alias')):
                        self.validate_account_credentials(deployment)
                    if deployment.get('skip-npm-ci'):
                        deploy_opts = {'skip-npm-ci': True}
                    else:
                        deploy_opts = {}
                    for module in deployment.get('modules', []):
                        module_root = os.path.join(self.env_root, module)
                        with self.change_dir(module_root):
                            getattr(Module(options=self.options,
                                           env_vars=self.env_vars,
                                           env_root=self.env_root,
                                           deploy_opts=deploy_opts,
                                           module_root=module_root),
                                    command)()
                    if deployment.get('current_dir', False):
                        getattr(Module(options=self.options,
                                       env_vars=self.env_vars,
                                       env_root=self.env_root,
                                       deploy_opts=deploy_opts,
                                       module_root=self.env_root),
                                command)()
                if deployment.get('assume-role'):
                    self.post_deploy_assume_role(deployment['assume-role'])

    def plan(self, deployments=None):
        """Plan apps/code deployment."""
        self.run(deployments=deployments, command='plan')

    def deploy(self, deployments=None):
        """Deploy apps/code."""
        self.run(deployments=deployments, command='deploy')

    def destroy(self, deployments=None):
        """Deploy apps/code."""
        self.run(deployments=deployments, command='destroy')

    def validate_account_credentials(self, deployment=None):
        """Exit if requested deployment account doesn't match credentials."""
        if deployment is None:
            deployment = {}
        boto_args = {'region_name': self.env_vars['AWS_DEFAULT_REGION']}
        for i in ['aws_access_key_id', 'aws_secret_access_key',
                  'aws_session_token']:
            if self.env_vars.get(i.upper()):
                boto_args[i] = self.env_vars[i.upper()]
        if isinstance(deployment.get('account-id'), (int, str, unicode)):
            account_id = str(deployment['account-id'])
        elif deployment.get('account-id', {}).get(self.environment_name):
            account_id = str(deployment['account-id'][self.environment_name])
        else:
            account_id = None
        if account_id:
            self.validate_account_id(boto3.client('sts', **boto_args),
                                     account_id)
        if isinstance(deployment.get('account-alias'), (str, unicode)):
            account_alias = deployment['account-alias']
        elif deployment.get('account-alias', {}).get(self.environment_name):
            account_alias = deployment['account-alias'][self.environment_name]
        else:
            account_alias = None
        if account_alias:
            self.validate_account_alias(boto3.client('iam', **boto_args),
                                        account_alias)

    def execute(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the execute() method '
                                  'yourself!')

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
        elif selected_index == '':
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

    @staticmethod
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

    @staticmethod
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
