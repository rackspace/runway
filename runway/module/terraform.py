"""Terraform module."""
import copy
import json
import logging
import os
import re
import subprocess
import sys
import warnings

import boto3
from send2trash import send2trash
import six

from . import RunwayModule, run_module_command
from ..env_mgr.tfenv import TFEnvManager
from ..util import (
    change_dir, extract_boto_args_from_env, find_cfn_output,
    merge_nested_environment_dicts, which
)

FAILED_INIT_FILENAME = '.init_failed'
LOGGER = logging.getLogger('runway')


def create_config_backend_options(module_opts, env_name, env_vars):
    """Return backend options defined in module options."""
    backend_opts = {}

    if module_opts.get('terraform_backend_config'):
        backend_opts['config'] = merge_nested_environment_dicts(
            module_opts.get('terraform_backend_config'),
            env_name
        )
    if module_opts.get('terraform_backend_cfn_outputs'):
        if not backend_opts.get('config'):
            backend_opts['config'] = {}
        if not backend_opts['config'].get('region'):
            backend_opts['config']['region'] = env_vars['AWS_DEFAULT_REGION']

        boto_args = extract_boto_args_from_env(env_vars)
        cfn_client = boto3.client(
            'cloudformation',
            region_name=backend_opts['config']['region'],
            **boto_args
        )
        for (key, val) in merge_nested_environment_dicts(module_opts.get('terraform_backend_cfn_outputs'),  # noqa pylint: disable=line-too-long
                                                         env_name).items():
            backend_opts['config'][key] = find_cfn_output(
                val.split('::')[1],
                cfn_client.describe_stacks(
                    StackName=val.split('::')[0]
                )['Stacks'][0]['Outputs']
            )
    if module_opts.get('terraform_backend_ssm_params'):
        dep_msg = ('Use of the "terraform_backend_ssm_params" option has been '
                   'deprecated. The "terraform_backend_config" option with '
                   '"ssm" lookup should be used instead.')
        warnings.warn(dep_msg, DeprecationWarning)
        LOGGER.warning(dep_msg)
        if not backend_opts.get('config'):
            backend_opts['config'] = {}
        if not backend_opts['config'].get('region'):
            backend_opts['config']['region'] = env_vars['AWS_DEFAULT_REGION']

        boto_args = extract_boto_args_from_env(env_vars)
        ssm_client = boto3.client(
            'ssm',
            region_name=backend_opts['config']['region'],
            **boto_args
        )
        for (key, val) in merge_nested_environment_dicts(module_opts.get('terraform_backend_ssm_params'),  # noqa pylint: disable=line-too-long
                                                         env_name).items():
            backend_opts['config'][key] = ssm_client.get_parameter(
                Name=val
            )['Parameter']['Value']

    return backend_opts


def get_backend_init_list(backend_vals):
    """Turn backend config dict into command line items."""
    cmd_list = []
    for (key, val) in backend_vals.items():
        if val:
            cmd_list.append('-backend-config')
            cmd_list.append(key + '=' + val)
        else:
            LOGGER.warning("Skipping terraform backend config option \"%s\" "
                           "-- no value provided", key)
    return cmd_list


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


def get_module_defined_tf_var(terraform_version_opts, env_name):
    """Return version of Terraform requested in module options."""
    if isinstance(terraform_version_opts, six.string_types):
        return terraform_version_opts
    if terraform_version_opts.get(env_name):
        return terraform_version_opts.get(env_name)
    if terraform_version_opts.get('*'):
        return terraform_version_opts.get('*')
    return None


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


def run_terraform_init(tf_bin,  # pylint: disable=too-many-arguments
                       module_path, backend_options, env_name, env_region,
                       env_vars):
    """Run Terraform init."""
    init_cmd = [tf_bin, 'init', '-reconfigure']
    cmd_opts = {'env_vars': env_vars, 'exit_on_error': False}

    if backend_options.get('config'):
        LOGGER.info('Using provided backend values "%s"',
                    str(backend_options.get('config')))
        cmd_opts['cmd_list'] = init_cmd + get_backend_init_list(backend_options.get('config'))  # noqa pylint: disable=line-too-long
    elif os.path.isfile(os.path.join(module_path,
                                     backend_options.get('filename'))):
        LOGGER.info('Using backend config file %s',
                    backend_options.get('filename'))
        cmd_opts['cmd_list'] = init_cmd + ['-backend-config=%s' % backend_options.get('filename')]  # noqa pylint: disable=line-too-long
    else:
        LOGGER.info(
            "No backend tfvars file found -- looking for one "
            "of \"%s\" (proceeding with bare 'terraform "
            "init')",
            ', '.join(gen_backend_tfvars_files(
                env_name,
                env_region)))
        cmd_opts['cmd_list'] = init_cmd

    try:
        run_module_command(**cmd_opts)
    except subprocess.CalledProcessError as shelloutexc:
        # An error during initialization can leave things in an inconsistent
        # state (e.g. backend configured but no providers downloaded). Marking
        # this with a file so it will be deleted on the next run.
        if os.path.isdir(os.path.join(module_path, '.terraform')):
            with open(os.path.join(module_path,
                                   '.terraform',
                                   FAILED_INIT_FILENAME), 'w') as stream:
                stream.write('1')
        sys.exit(shelloutexc.returncode)


def update_env_vars_with_tf_var_values(os_env_vars, tf_vars):
    """Return os_env_vars with TF_VAR_ values for each tf_var."""
    # https://www.terraform.io/docs/commands/environment-variables.html#tf_var_name
    for (key, val) in tf_vars.items():
        if isinstance(val, dict):
            os_env_vars["TF_VAR_%s" % key] = "{ %s }" % str(
                # e.g. TF_VAR_amap='{ foo = "bar", baz = "qux" }'
                ', '.join([nestedkey + ' = "' + nestedval + '"'
                           for (nestedkey, nestedval) in val.items()])
            )
        elif isinstance(val, list):
            os_env_vars["TF_VAR_%s" % key] = json.dumps(val)
        else:
            os_env_vars["TF_VAR_%s" % key] = val
    return os_env_vars


class Terraform(RunwayModule):
    """Terraform Runway Module."""

    def run_terraform(self, command='plan'):  # noqa pylint: disable=too-many-branches,too-many-statements
        """Run Terraform."""
        response = {'skipped_configs': False}
        tf_cmd = [command]

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
        backend_options = create_config_backend_options(self.options.get('options', {}),  # noqa
                                                        self.context.env_name,
                                                        self.context.env_vars)
        # This filename will only be used if it exists
        backend_options['filename'] = get_backend_tfvars_file(
            self.path,
            self.context.env_name,
            self.context.env_region
        )
        workspace_tfvar_present = os.path.isfile(
            os.path.join(self.path, workspace_tfvars_file)
        )
        if workspace_tfvar_present:
            tf_cmd.append("-var-file=%s" % workspace_tfvars_file)
        env_vars = copy.deepcopy(self.context.env_vars)
        env_vars = update_env_vars_with_tf_var_values(
            env_vars,
            self.options['parameters']
        )

        if self.options['parameters'] or workspace_tfvar_present:
            LOGGER.info("Preparing to run terraform %s on %s...",
                        command,
                        os.path.basename(self.path))
            module_defined_tf_var = get_module_defined_tf_var(
                self.options.get('options', {}).get('terraform_version', {}),
                self.context.env_name
            )
            if module_defined_tf_var:
                tf_bin = TFEnvManager(self.path).install(module_defined_tf_var)
            elif os.path.isfile(os.path.join(self.path,
                                             '.terraform-version')):
                tf_bin = TFEnvManager(self.path).install()
            elif os.path.isfile(os.path.join(self.context.env_root,
                                             '.terraform-version')):
                tf_bin = TFEnvManager(self.context.env_root).install()
            else:
                if not which('terraform'):
                    LOGGER.error('Terraform not available (a '
                                 '".terraform-version" file is not present '
                                 'and "terraform" not found in path). Fix '
                                 'this by writing a desired Terraform version '
                                 'to your module\'s .terraform-version file '
                                 'or installing Terraform.')
                    sys.exit(1)
                tf_bin = 'terraform'
            tf_cmd.insert(0, tf_bin)
            with change_dir(self.path):
                if os.path.isfile(os.path.join(self.path, '.terraform', FAILED_INIT_FILENAME)):
                    LOGGER.info('Previous init failed; trashing '
                                '.terraform directory...')
                    send2trash(os.path.join(self.path, '.terraform'))

                LOGGER.info('Running "terraform init"...')
                run_terraform_init(
                    tf_bin=tf_bin,
                    module_path=self.path,
                    backend_options=backend_options,
                    env_name=self.context.env_name,
                    env_region=self.context.env_region,
                    env_vars=env_vars
                )

                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    [tf_bin,
                     'workspace',
                     'show'],
                    env=env_vars
                ).strip().decode()
                if current_tf_workspace != self.context.env_name:
                    LOGGER.info("Terraform workspace currently set to %s; "
                                "switching to %s...",
                                current_tf_workspace,
                                self.context.env_name)
                    LOGGER.debug('Checking available Terraform '
                                 'workspaces...')
                    available_tf_envs = subprocess.check_output(
                        [tf_bin, 'workspace', 'list'],
                        env=env_vars
                    ).decode()
                    if re.compile("^[*\\s]\\s%s$" % self.context.env_name,
                                  re.M).search(available_tf_envs):
                        run_module_command(
                            cmd_list=[tf_bin, 'workspace', 'select',
                                      self.context.env_name],
                            env_vars=env_vars
                        )
                    else:
                        LOGGER.info("Terraform workspace %s not found; "
                                    "creating it...",
                                    self.context.env_name)
                        run_module_command(
                            cmd_list=[tf_bin, 'workspace', 'new',
                                      self.context.env_name],
                            env_vars=env_vars
                        )
                    LOGGER.info('Re-running terraform init after workspace '
                                'change...')
                    run_terraform_init(
                        tf_bin=tf_bin,
                        module_path=self.path,
                        backend_options=backend_options,
                        env_name=self.context.env_name,
                        env_region=self.context.env_region,
                        env_vars=env_vars
                    )
                LOGGER.info('Executing "terraform get" to update remote '
                            'modules')
                run_module_command(
                    cmd_list=[tf_bin, 'get', '-update=true'],
                    env_vars=env_vars
                )
                LOGGER.info("Running Terraform %s on %s (\"%s\")",
                            command,
                            os.path.basename(self.path),
                            " ".join(tf_cmd))
                if any(key.startswith('TF_VAR_') for key, _val in env_vars.items()):
                    LOGGER.info(
                        "With terraform variable environment variables \"%s\"",
                        " ".join(
                            ["%s=%s" % (key, val)
                             for key, val in env_vars.items()
                             if key.startswith('TF_VAR_')]
                        )
                    )
                run_module_command(cmd_list=tf_cmd,
                                   env_vars=env_vars)
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
        self.run_terraform(command='plan')

    def deploy(self):
        """Run tf apply."""
        self.run_terraform(command='apply')

    def destroy(self):
        """Run tf destroy."""
        self.run_terraform(command='destroy')
