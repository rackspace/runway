"""runway env module."""
from __future__ import print_function

# pylint trips up on this in virtualenv
# https://github.com/PyCQA/pylint/issues/73
from distutils.util import strtobool  # noqa pylint: disable=no-name-in-module,import-error

from subprocess import check_call, check_output

import json
import logging
import os
import shutil
import sys

from builtins import input  # pylint: disable=redefined-builtin

from .base import Base
from .module import Module

logging.basicConfig(level=logging.INFO)
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
        if self.env_vars.get('CI', None):
            deployments_to_run = deployments
        else:
            deployments_to_run = self.select_deployment_to_run(deployments)
        for deployment in deployments_to_run:
            if deployment.get('regions'):
                for region in deployment['regions']:
                    if deployment.get('assume-role'):
                        self.pre_deploy_assume_role(deployment['assume-role'],
                                                    region)
                    self.update_env_vars({'AWS_DEFAULT_REGION': region})
                    for module in deployment.get('modules', []):
                        module_root = os.path.join(self.env_root, module)
                        with self.change_dir(module_root):
                            getattr(Module(options=self.options,
                                           env_vars=self.env_vars,
                                           env_root=self.env_root,
                                           module_root=module_root),
                                    command)()
                    if deployment.get('current_dir', False):
                        getattr(Module(options=self.options,
                                       env_vars=self.env_vars,
                                       env_root=self.env_root,
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

    def execute(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the execute() method '
                                  'yourself!')

    @staticmethod
    def select_deployment_to_run(deployments=None):  # noqa pylint: disable=too-many-branches
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
            selected_index = input('Enter number of module to deploy '
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
