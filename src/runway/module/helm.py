"""K8s Helm module."""

import logging
import os
import subprocess

from runway.module import RunwayModule
from runway.env_mgr.helmenv import HelmEnvManager

LOGGER = logging.getLogger('runway')


class Helm(RunwayModule):
    """Helm Runway Module."""

    def run(self, command='plan'):
        """Run Helm Runway Module."""
        LOGGER.info('Running helm: %s', command)

        # Install Helm
        binary_file = HelmEnvManager(self.path).install('3.0.0')

        # Create Helm application name
        module_name = os.path.basename(self.path)
        env_name = self.context.env_name
        application_name = '%s-%s' % (module_name, env_name)

        # Execute command
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
        LOGGER.info('Running helm %s ("%s")...', command, ' '.join(cmd))
        response = subprocess.check_output(cmd, env=self.context.env_vars)
        if isinstance(response, bytes):  # python3 returns encoded bytes
            response = response.decode()
        print(response)

        # Response
        skipped_configs = command == "plan"
        return {'skipped_configs': skipped_configs}

    def plan(self):
        """Run plan."""
        self.run(command='plan')

    def deploy(self):
        """Run deploy."""
        self.run(command='deploy')

    def destroy(self):
        """Run destroy."""
        self.run(command='destroy')
