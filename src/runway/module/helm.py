"""K8s Helm module."""
from __future__ import print_function

import logging
import os
import subprocess
import sys

from runway.module import RunwayModule
from runway.env_mgr.helmenv import HelmEnvManager

LOGGER = logging.getLogger('runway')


class Helm(RunwayModule):
    """Helm Runway Module."""

    def run_helm(self, command='plan'):
        """Run Helm Runway Module."""
        LOGGER.info('Running helm: %s', command)

        # Install Helm
        binary_file = HelmEnvManager(self.path).install()

        # Create Helm application name
        module_name = os.path.basename(self.path)
        env_name = self.context.env_name
        application_name = '%s-%s' % (module_name, env_name)

        # Create command
        response = None
        cmd = None
        if command in ['plan', 'deploy']:
            cmd = [
                binary_file,
                'upgrade',
                '--install',
                '--history-max',
                '1',
                application_name,
                self.path
            ]
            if command == 'plan':
                cmd.append('--dry-run')
        elif command == 'destroy':
            cmd = [
                binary_file,
                'uninstall',
                application_name
            ]

        # execute command
        LOGGER.info('Running helm %s ("%s")...', command, ' '.join(cmd))
        response = subprocess.check_output(cmd, env=self.context.env_vars)
        if isinstance(response, bytes):  # python3 returns encoded bytes
            response = response.decode()
        LOGGER.info(response)

        # check deploy response
        if command == 'deploy':
            if 'STATUS: deployed' not in response:
                LOGGER.error('Helm failed to deploy chart.')
                sys.exit(1)

        # check destroy response
        if command == 'destroy':
            if 'uninstalled' not in response:
                LOGGER.error('Helm failed to destroy chart.')
                sys.exit(1)

        # Response
        skipped_configs = command == "plan"
        return {'skipped_configs': skipped_configs}

    def plan(self):
        """Run plan."""
        self.run_helm(command='plan')

    def deploy(self):
        """Run deploy."""
        self.run_helm(command='deploy')

    def destroy(self):
        """Run destroy."""
        self.run_helm(command='destroy')
