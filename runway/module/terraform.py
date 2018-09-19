"""Terraform module."""

import logging
import os
import re
import subprocess
import sys

from future.utils import viewitems
import hcl
from send2trash import send2trash

from . import RunwayModule, run_module_command, warn_on_skipped_configs
from ..util import change_dir, which

LOGGER = logging.getLogger('runway')


def gen_backend_tfvars_files(environment, region):
    """Generate possible Terraform backend tfvars filenames."""
    return [
        "backend-%s-%s.tfvars" % (environment, region),
        "backend-%s.tfvars" % environment,
        "backend-%s.tfvars" % region,
        "backend.tfvars"
    ]


def get_backend_tfvars_file(path, environment, region):
    """Determine Terraform backend file."""
    backend_filenames = gen_backend_tfvars_files(environment, region)
    for name in backend_filenames:
        if os.path.isfile(os.path.join(path, name)):
            return name
    return backend_filenames[-1]  # file not found; fallback to last item


def gen_workspace_tfvars_files(environment, region):
    """Generate possible Terraform workspace tfvars filenames."""
    return [
        # Give preference to explicit environment-region files
        "%s-%s.tfvars" % (environment, region),
        # Fallback to environment name only
        "%s.tfvars" % environment
    ]


def get_workspace_tfvars_file(path, environment, region):
    """Determine Terraform workspace-specific tfvars file name."""
    for name in gen_workspace_tfvars_files(environment, region):
        if os.path.isfile(os.path.join(path, name)):
            return name
    return "%s.tfvars" % environment  # fallback to generic name


def remove_stale_tf_config(path, backend_tfvars_file):
    """Ensure TF is ready for init.

    If deploying a TF module to multiple regions (or any scenario requiring
    multiple backend configs), switching the backend will cause TF to
    compare the old and new backends. This will frequently cause an access
    error as the creds/role for the new backend won't always have access to
    the old one.

    This method compares the defined & initialized backend configs and
    trashes the terraform directory if they're out of sync.
    """
    terrform_dir = os.path.join(path, '.terraform')
    tfstate_filepath = os.path.join(terrform_dir, 'terraform.tfstate')
    if os.path.isfile(tfstate_filepath):
        LOGGER.debug('Comparing previous & desired Terraform backend '
                     'configs')
        with open(tfstate_filepath, 'r') as fco:
            state_config = hcl.load(fco)

        if state_config.get('backend') and state_config['backend'].get('config'):  # noqa
            backend_tfvars_filepath = os.path.join(path,
                                                   backend_tfvars_file)
            with open(backend_tfvars_filepath, 'r') as fco:
                backend_config = hcl.load(fco)
            if any(state_config['backend']['config'][key] != value for (key, value) in viewitems(backend_config)):  # noqa pylint: disable=line-too-long
                LOGGER.info("Desired and previously initialized TF "
                            "backend config is out of sync; trashing "
                            "local TF state directory %s",
                            terrform_dir)
                send2trash(terrform_dir)


def run_terraform_init(module_path, backend_file_name, env_name, env_region,
                       env_vars):
    """Run Terraform init."""
    init_cmd = ['terraform', 'init']
    if os.path.isfile(os.path.join(module_path, backend_file_name)):  # noqa
        LOGGER.info('Using backend config file %s',
                    backend_file_name)
        remove_stale_tf_config(module_path, backend_file_name)
        run_module_command(
            cmd_list=init_cmd + ['-backend-config=%s' % backend_file_name],  # noqa pylint: disable=line-too-long
            env_vars=env_vars
        )
    else:
        LOGGER.info(
            "No backend tfvars file found -- looking for one "
            "of \"%s\" (proceeding with bare 'terraform "
            "init')",
            ', '.join(gen_backend_tfvars_files(
                env_name,
                env_region)))
        run_module_command(cmd_list=init_cmd,
                           env_vars=env_vars)


def run_tfenv_install(path, env_vars):
    """Ensure appropriate Terraform version is installed."""
    if which('tfenv') is None:
        LOGGER.error('"tfenv" not found (and a Terraform version is '
                     'specified in .terraform-version). Please install '
                     'tfenv.')
        sys.exit(1)
    with change_dir(path):
        subprocess.check_call(['tfenv', 'install'], env=env_vars)


class Terraform(RunwayModule):
    """Terraform Runway Module."""

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

        workspace_tfvars_file = get_workspace_tfvars_file(self.path,
                                                          self.context.env_name,  # noqa
                                                          self.context.env_region)  # noqa
        backend_tfvars_file = get_backend_tfvars_file(self.path,
                                                      self.context.env_name,
                                                      self.context.env_region)
        workspace_tfvar_present = os.path.isfile(
            os.path.join(self.path, workspace_tfvars_file)
        )
        if workspace_tfvar_present:
            tf_cmd.append("-var-file=%s" % workspace_tfvars_file)
        if isinstance(self.options.get('environments',
                                       {}).get(self.context.env_name),
                      dict):
            for (key, val) in self.options['environments'][self.context.env_name].items():  # noqa
                tf_cmd.extend(['-var', "%s=%s" % (key, val)])

        if self.options.get('environments', {}).get(self.context.env_name) or (
                workspace_tfvar_present):
            LOGGER.info("Preparing to run terraform %s on %s...",
                        command,
                        os.path.basename(self.path))
            if os.path.isfile(os.path.join(self.path,
                                           '.terraform-version')):
                run_tfenv_install(self.path, self.context.env_vars)
            with change_dir(self.path):
                if not os.path.isdir(os.path.join(self.path,
                                                  '.terraform')):
                    LOGGER.info('.terraform directory missing; running '
                                '"terraform init"...')
                    run_terraform_init(
                        module_path=self.path,
                        backend_file_name=backend_tfvars_file,
                        env_name=self.context.env_name,
                        env_region=self.context.env_region,
                        env_vars=self.context.env_vars
                    )
                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    ['terraform',
                     'workspace',
                     'show'],
                    env=self.context.env_vars
                ).strip().decode()
                if current_tf_workspace != self.context.env_name:
                    LOGGER.info("Terraform workspace current set to %s; "
                                "switching to %s...",
                                current_tf_workspace,
                                self.context.env_name)
                    LOGGER.debug('Checking available Terraform '
                                 'workspaces...')
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
                    run_terraform_init(
                        module_path=self.path,
                        backend_file_name=backend_tfvars_file,
                        env_name=self.context.env_name,
                        env_region=self.context.env_region,
                        env_vars=self.context.env_vars
                    )
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
                            os.path.basename(self.path),
                            " ".join(tf_cmd))
                run_module_command(cmd_list=tf_cmd,
                                   env_vars=self.context.env_vars)
        else:
            response['skipped_configs'] = True
            LOGGER.info("Skipping Terraform %s of %s",
                        command,
                        os.path.basename(self.path))
            LOGGER.info(
                "(no tfvars file for this environment/region found -- looking "
                "for one of \"%s\")",
                ', '.join(gen_workspace_tfvars_files(
                    self.context.env_name,
                    self.context.env_region)))
        return response

    def plan(self):
        """Run tf plan."""
        result = self.run_terraform(command='plan')
        warn_on_skipped_configs(result, self.context.env_name,
                                self.context.env_vars)

    def deploy(self):
        """Run tf apply."""
        result = self.run_terraform(command='apply')
        warn_on_skipped_configs(result, self.context.env_name,
                                self.context.env_vars)

    def destroy(self):
        """Run tf destroy."""
        result = self.run_terraform(command='destroy')
        warn_on_skipped_configs(result, self.context.env_name,
                                self.context.env_vars)
