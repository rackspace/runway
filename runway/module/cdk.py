"""CDK module."""

import logging
import os
import subprocess
import sys

from . import (
    RunwayModule, format_npm_command_for_logging, generate_node_command,
    run_module_command, run_npm_install, warn_on_boto_env_vars
)
from ..util import (
    change_dir, run_commands, which
)

LOGGER = logging.getLogger('runway')


def get_cdk_stacks(module_path, env_vars, context_opts):
    """Return list of CDK stacks."""
    LOGGER.debug('Listing stacks in the CDK app prior to '
                 'diff')
    result = subprocess.check_output(
        generate_node_command(
            command='cdk',
            command_opts=['list'] + context_opts,
            path=module_path),
        env=env_vars
    )
    if isinstance(result, bytes):  # python3 returns encoded bytes
        result = result.decode()
    return result.strip().split('\n')


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

        warn_on_boto_env_vars(self.context.env_vars)

        if self.options['environment']:
            if os.path.isfile(os.path.join(self.path, 'package.json')):
                with change_dir(self.path):
                    run_npm_install(self.path, self.options, self.context)
                    if self.options.get('options', {}).get('build_steps',
                                                           []):
                        LOGGER.info("Running build steps for %s...",
                                    os.path.basename(self.path))
                        run_commands(
                            commands=self.options.get('options',
                                                      {}).get('build_steps',
                                                              []),
                            directory=self.path,
                            env=self.context.env_vars
                        )
                    cdk_context_opts = []
                    for (key, val) in self.options['parameters'].items():
                        cdk_context_opts.extend(['-c', "%s=%s" % (key, val)])
                    cdk_opts.extend(cdk_context_opts)
                    if command == 'diff':
                        LOGGER.info("Running cdk %s on each stack in %s",
                                    command,
                                    os.path.basename(self.path))
                        for i in get_cdk_stacks(self.path,
                                                self.context.env_vars,
                                                cdk_context_opts):
                            subprocess.call(
                                generate_node_command(
                                    'cdk',
                                    cdk_opts + [i],  # 'diff <stack>'
                                    self.path
                                ),
                                env=self.context.env_vars
                            )
                    else:
                        # Make sure we're targeting all stacks
                        if command in ['deploy', 'destroy']:
                            cdk_opts.append('"*"')

                        if command == 'deploy':
                            if 'CI' in self.context.env_vars:
                                cdk_opts.append('--ci')
                                cdk_opts.append('--require-approval=never')
                            bootstrap_command = generate_node_command(
                                'cdk',
                                ['bootstrap'] + cdk_context_opts,
                                self.path
                            )
                            LOGGER.info('Running cdk bootstrap...')
                            run_module_command(cmd_list=bootstrap_command,
                                               env_vars=self.context.env_vars)
                        elif command == 'destroy' and 'CI' in self.context.env_vars:  # noqa
                            cdk_opts.append('-f')  # Don't prompt
                        cdk_command = generate_node_command(
                            'cdk',
                            cdk_opts,
                            self.path
                        )
                        LOGGER.info("Running cdk %s on %s (\"%s\")",
                                    command,
                                    os.path.basename(self.path),
                                    format_npm_command_for_logging(cdk_command))  # noqa
                        run_module_command(cmd_list=cdk_command,
                                           env_vars=self.context.env_vars)
            else:
                LOGGER.info(
                    "Skipping cdk %s of %s; no \"package.json\" "
                    "file was found (need a package file specifying "
                    "aws-cdk in devDependencies)",
                    command,
                    os.path.basename(self.path))
        else:
            LOGGER.info(
                "Skipping cdk %s of %s; no config for "
                "this environment found or current account/region does not "
                "match configured environment",
                command,
                os.path.basename(self.path))
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
