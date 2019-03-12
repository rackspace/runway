"""CDK module."""

import logging
import os
import subprocess
import sys

import boto3
import six

from . import RunwayModule, run_module_command
from ..util import change_dir, run_commands, which

LOGGER = logging.getLogger('runway')


def cdk_module_matches_env(env_name, env_config, env_vars):
    """Return bool on whether cdk command should continue in current env."""
    if env_config.get(env_name):
        current_env_config = env_config[env_name]
        if isinstance(current_env_config, type(True)) and current_env_config:
            return True
        if isinstance(current_env_config, six.string_types):
            (account_id, region) = current_env_config.split('/')
            if region == env_vars['AWS_DEFAULT_REGION']:
                boto_args = {}
                for i in ['aws_access_key_id', 'aws_secret_access_key',
                          'aws_session_token']:
                    if env_vars.get(i.upper()):
                        boto_args[i] = env_vars[i.upper()]
                sts_client = boto3.client(
                    'sts',
                    region_name=env_vars['AWS_DEFAULT_REGION'],
                    **boto_args
                )
                if sts_client.get_caller_identity()['Account'] == account_id:
                    return True
    return False


def get_cdk_stacks(npm_helper, module_path, env_vars):
    """Return list of CDK stacks."""
    LOGGER.debug('Listing stacks in the CDK app prior to '
                 'diff')
    return subprocess.check_output(
        npm_helper.generate_node_command(
            command='cdk',
            command_opts=['list'],
            path=module_path),
        env=env_vars
    ).strip().split('\n')


def run_pipenv_sync(path):
    """Ensure python libraries are up to date, if applicable."""
    if os.path.isfile(os.path.join(path, 'Pipfile.lock')):
        LOGGER.info('Module has a Pipfile.lock file defining python '
                    'dependencies; invocating pipenv to install/update '
                    'them...')
        pipenv_path = which('pipenv')
        if not pipenv_path:
            LOGGER.error('"pipenv" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)
        subprocess.check_call([pipenv_path, 'sync', '-d', '--three'])


class CloudDevelopmentKit(RunwayModule):
    """CDK Runway Module."""

    def run_cdk(self, command='deploy'):  # pylint: disable=too-many-branches
        """Run CDK."""
        response = {'skipped_configs': False}
        cdk_opts = [command]

        if not which('npm'):
            LOGGER.error('"npm" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if 'DEBUG' in self.context.env_vars:
            cdk_opts.append('-v')  # Increase logging if requested

        if cdk_module_matches_env(self.context.env_name,
                                  self.environment_options,
                                  self.context.env_vars):
            if self.folder.isfile('package.json'):
                with change_dir(self.path):
                    self.npm.run_npm_install()
                    run_pipenv_sync(self.path)
                    build_steps = self.module_options.get('build_steps', [])
                    if build_steps:
                        LOGGER.info("Running build steps for %s...", self.name)
                        run_commands(
                            commands=build_steps,
                            directory=self.path,
                            env=self.context.env_vars
                        )
                    if command == 'diff':
                        LOGGER.info("Running cdk %s on each stack in %s",
                                    command,
                                    self.name)
                        for i in get_cdk_stacks(self.npm,
                                                self.path,
                                                self.context.env_vars):
                            subprocess.call(
                                self.npm.generate_node_command(
                                    'cdk',
                                    cdk_opts + [i],  # 'diff <stack>'
                                    self.path
                                ),
                                env=self.context.env_vars
                            )
                    else:
                        if command == 'deploy':
                            if 'CI' in self.context.env_vars:
                                cdk_opts.append('--require-approval=never')
                            bootstrap_command = self.npm.generate_node_command(
                                'cdk',
                                ['bootstrap'],
                                self.path
                            )
                            LOGGER.info('Running cdk bootstrap...')
                            run_module_command(cmd_list=bootstrap_command,
                                               env_vars=self.context.env_vars)
                        elif command == 'destroy' and 'CI' in self.context.env_vars:  # noqa
                            cdk_opts.append('-f')  # Don't prompt
                        cdk_command = self.npm.generate_node_command(
                            'cdk',
                            cdk_opts,
                            self.path
                        )
                        LOGGER.info("Running cdk %s on %s (\"%s\")",
                                    command,
                                    self.name,
                                    self.npm.format_npm_command_for_logging(cdk_command))  # noqa
                        run_module_command(cmd_list=cdk_command,
                                           env_vars=self.context.env_vars)
            else:
                LOGGER.info(
                    "Skipping cdk %s of %s; no \"package.json\" "
                    "file was found (need a package file specifying "
                    "aws-cdk in devDependencies)",
                    command,
                    self.name)
        else:
            LOGGER.info(
                "Skipping cdk %s of %s; no config for "
                "this environment found or current account/region does not "
                "match configured environment",
                command,
                self.name)
            response['skipped_configs'] = True
        return response

    def plan(self):
        """Run cdk diff."""
        self.run_cdk(command='diff')

    def deploy(self):
        """Run cdk deploy."""
        self.run_cdk(command='deploy')

    def destroy(self):
        """Run cdk destroy."""
        self.run_cdk(command='destroy')
