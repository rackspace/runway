"""Terraform module."""

import logging
import os
import platform
import re
import subprocess
import sys

from future.utils import viewitems
from send2trash import send2trash

from . import RunwayModule, run_module_command
from ..util import change_dir, which

LOGGER = logging.getLogger('runway')


def get_backend_init_list(backend_vals):
    """Turn backend config dict into command line items."""
    cmd_list = []
    for (key, val) in backend_vals.items():
        cmd_list.append('-backend-config')
        cmd_list.append(key + '=' + val)
    return cmd_list


def run_tfenv_install(path, env_vars):
    """Ensure appropriate Terraform version is installed."""
    if which('tfenv') is None:
        if platform.system().lower() == 'windows':
            LOGGER.warning('A required Terraform version for this module is '
                           'specified in a .terraform-version file for use '
                           'with tfenv (which is unfortunately not available '
                           'for Windows). Please ensure your Terraform version '
                           'matches the version in this file.')
            return False
        LOGGER.error('"tfenv" not found (and a Terraform version is specified '
                     'in this module\'s .terraform-version file). Please '
                     'install tfenv.')
        sys.exit(1)
    with change_dir(path):
        subprocess.check_call(['tfenv', 'install'], env=env_vars)
        return True


class Terraform(RunwayModule):
    """Terraform Runway Module."""

    def gen_backend_tfvars_files(self):
        """Generate possible Terraform backend tfvars filenames."""
        return [
            "backend-%s-%s.tfvars" % (self.context.env_name, self.context.env_region),
            "backend-%s.tfvars" % self.context.env_name,
            "backend-%s.tfvars" % self.context.env_region,
            "backend.tfvars"
        ]

    def get_backend_tfvars_file(self):
        """Determine Terraform backend file."""
        return self.loader.locate_env_file(self.gen_backend_tfvars_files())

    def gen_workspace_tfvars_files(self):
        """Generate possible Terraform workspace tfvars filenames."""
        return [
            # Give preference to explicit environment-region files
            "%s-%s.tfvars" % (self.context.env_name, self.context.env_region),
            # Fallback to environment name only
            "%s.tfvars" % self.context.env_name
        ]

    def get_workspace_tfvars_file(self):
        """Determine Terraform workspace-specific tfvars file name."""
        return self.loader.locate_env_file(self.gen_workspace_tfvars_files())

    def run_terraform_init(self, backend_options):
        """Run Terraform init."""
        init_cmd = ['terraform', 'init']
        if backend_options.get('config'):
            LOGGER.info('Using provided backend values "%s"', str(backend_options.get('config')))
            self.remove_stale_tf_config(backend_options)
            run_module_command(
                cmd_list=init_cmd + get_backend_init_list(backend_options.get('config')),
                env_vars=self.context.env_vars
            )
        elif self.path.isfile(backend_options.get('filename')):
            LOGGER.info('Using backend config file %s', backend_options.get('filename'))
            self.remove_stale_tf_config(backend_options)
            run_module_command(
                cmd_list=init_cmd + ['-backend-config=%s' % backend_options.get('filename')],
                env_vars=self.context.env_vars
            )
        else:
            LOGGER.info(
                "No backend tfvars file found -- looking for one "
                "of \"%s\" (proceeding with bare 'terraform "
                "init')",
                ', '.join(self.gen_backend_tfvars_files()))
            run_module_command(cmd_list=init_cmd,
                               env_vars=self.context.env_vars)

    def prep_workspace_switch(self, backend_options):
        """Clean terraform directory and run init if necessary.

        Creating a new workspace after a previous workspace has been created with
        a defined 'key' will result in the new workspace retaining the same key.
        Additionally, existing workspaces will not show up in a `tf workspace
        list` if they have a different custom key than the previously
        initialized workspace.

        This function will check for a custom key and re-init.
        """
        terraform_dir = '.terraform'
        backend_filepath = backend_options.get('filename')
        if self.path.isdir(terraform_dir) and (
                backend_options.get('config') or self.path.isfile(backend_filepath)):
            if backend_options.get('config'):
                state_config = backend_options.get('config')
            else:
                state_config = self.loader.load_hcl_file(backend_filepath)
            if 'key' in state_config:
                LOGGER.info("Backend config defines a custom state key, "
                            "which Terraform will not respect when listing/"
                            "switching workspaces. Deleting the current "
                            ".terraform directory to ensure the key is used.")
                send2trash(terraform_dir)
                LOGGER.info(".terraform directory removed; proceeding with "
                            "init...")
                self.run_terraform_init(backend_options)

    def remove_stale_tf_config(self, backend_options):
        """Ensure TF is ready for init.

        If deploying a TF module to multiple regions (or any scenario requiring
        multiple backend configs), switching the backend will cause TF to
        compare the old and new backends. This will frequently cause an access
        error as the creds/role for the new backend won't always have access to
        the old one.

        This method compares the defined & initialized backend configs and
        trashes the terraform directory if they're out of sync.
        """
        terraform_dir = '.terraform'
        tfstate_filepath = os.path.join(terraform_dir, 'terraform.tfstate')
        if self.path.isfile(tfstate_filepath):
            LOGGER.debug('Comparing previous & desired Terraform backend configs')
            state_config = self.loader.load_hcl_file(tfstate_filepath)
            if state_config.get('backend') and state_config['backend'].get('config'):
                if backend_options.get('config'):
                    backend_config = backend_options.get('config')
                else:
                    backend_config = self.loader.load_hcl_file(backend_options.get('filename'))
                if any(state_config['backend']['config'][key] != value for (key, value) in viewitems(backend_config)):  # noqa pylint: disable=line-too-long
                    LOGGER.info("Desired and previously initialized TF "
                                "backend config is out of sync; trashing "
                                "local TF state directory %s",
                                terraform_dir)
                    send2trash(terraform_dir)

    def run_terraform(self, command='plan'):  # noqa pylint: disable=too-many-branches,too-many-statements
        """Run Terraform."""
        response = {'skipped_configs': False}
        tf_cmd = ['terraform', command]

        if not which('terraform'):
            LOGGER.error('"terraform" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if command == 'destroy':
            tf_cmd.append('-force')
        elif command == 'apply':
            if 'CI' in self.context.env_vars:
                tf_cmd.append('-auto-approve=true')
            else:
                tf_cmd.append('-auto-approve=false')

        workspace_tfvars_file = self.get_workspace_tfvars_file()
        workspace_tfvar_present = self.path.isfile(workspace_tfvars_file)

        backend_options = {
            'config': self.module_options.get('terraform_backend_config'),
            'filename': self.get_backend_tfvars_file()
        }

        if workspace_tfvar_present:
            tf_cmd.append("-var-file=%s" % workspace_tfvars_file)
        if self.environment_options:
            for (key, val) in self.environment_options.items():
                tf_cmd.extend(['-var', "%s=%s" % (key, val)])

        if self.environment_options or workspace_tfvar_present:
            LOGGER.info("Preparing to run terraform %s on %s...",
                        command,
                        self.name)
            if self.path.isfile('.terraform-version'):
                run_tfenv_install(self.path, self.context.env_vars)
            with change_dir(self.path):
                if not self.path.isdir('.terraform'):
                    LOGGER.info('.terraform directory missing; running '
                                '"terraform init"...')
                    self.run_terraform_init(backend_options)

                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    ['terraform',
                     'workspace',
                     'show'],
                    env=self.context.env_vars
                ).strip().decode()

                if current_tf_workspace != self.context.env_name:
                    LOGGER.info("Terraform workspace currently set to %s; "
                                "switching to %s...",
                                current_tf_workspace,
                                self.context.env_name)
                    LOGGER.debug('Checking available Terraform '
                                 'workspaces...')
                    self.prep_workspace_switch(backend_options=backend_options)
                    available_tf_envs = subprocess.check_output(
                        ['terraform', 'workspace', 'list'],
                        env=self.context.env_vars
                    ).decode()
                    if re.compile("^[*\\s]\\s%s$" % self.context.env_name,
                                  re.M).search(available_tf_envs):
                        run_module_command(
                            cmd_list=['terraform', 'workspace', 'select',
                                      self.context.env_name],
                            env_vars=self.context.env_vars
                        )
                    else:
                        LOGGER.info("Terraform workspace %s not found; "
                                    "creating it...",
                                    self.context.env_name)
                        run_module_command(
                            cmd_list=['terraform', 'workspace', 'new',
                                      self.context.env_name],
                            env_vars=self.context.env_vars
                        )
                    LOGGER.info('Running "terraform init" after workspace '
                                'creation/switch...')
                    self.run_terraform_init(backend_options=backend_options)

                if 'SKIP_TF_GET' not in self.context.env_vars:
                    LOGGER.info('Executing "terraform get" to update remote '
                                'modules')
                    run_module_command(
                        cmd_list=['terraform', 'get', '-update=true'],
                        env_vars=self.context.env_vars
                    )

                else:
                    LOGGER.info('Skipping "terraform get" due to '
                                '"SKIP_TF_GET" environment variable...')

                LOGGER.info("Running Terraform %s on %s (\"%s\")",
                            command,
                            self.name,
                            " ".join(tf_cmd))
                run_module_command(cmd_list=tf_cmd,
                                   env_vars=self.context.env_vars)
        else:
            response['skipped_configs'] = True
            LOGGER.info("Skipping Terraform %s of %s", command, self.name)
            LOGGER.info(
                "(no tfvars file for this environment/region found -- looking "
                "for one of \"%s\")",
                ', '.join(self.gen_workspace_tfvars_files()))

        return response

    def plan(self):
        """Run tf plan."""
        self.run_terraform(command='plan')

    def deploy(self):
        """Run tf apply."""
        self.run_terraform(command='apply')

    def destroy(self):
        """Run tf destroy."""
        self.run_terraform(command='destroy')
