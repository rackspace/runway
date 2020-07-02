"""Terraform module."""
import copy
import json
import logging
import os
import re
import subprocess
import sys
import warnings

from send2trash import send2trash
from six import string_types

from ..cfngin.lookups.handlers.output import deconstruct
from ..env_mgr.tfenv import TFEnvManager
from ..util import cached_property, change_dir, find_cfn_output, which
from . import ModuleOptions, RunwayModule, run_module_command

FAILED_INIT_FILENAME = '.init_failed'
LOGGER = logging.getLogger('runway')


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
                       module_path, module_options, env_name, env_region,
                       env_vars, no_color=False):
    """Run Terraform init."""
    cmd_opts = {'env_vars': env_vars,
                'exit_on_error': False,
                'cmd_list': [tf_bin, 'init', '-reconfigure']}
    if no_color:
        cmd_opts['cmd_list'].append('-no-color')

    if module_options.backend_config.init_args:
        LOGGER.info('Using provided backend values "%s"',
                    str(module_options.backend_config.init_args))
        cmd_opts['cmd_list'].extend(module_options.backend_config.init_args)
    elif module_options.backend_config.filename:
        LOGGER.info('Using backend config file %s',
                    module_options.backend_config.filename)
        cmd_opts['cmd_list'].append(
            '-backend-config=%s' % module_options.backend_config.filename
        )
    else:
        LOGGER.info(
            "No backend tfvars file found -- looking for one "
            "of \"%s\" (proceeding with bare 'terraform "
            "init')",
            ', '.join(
                module_options.backend_config.gen_backend_tfvars_filenames(
                    env_name,
                    env_region
                )))
    cmd_opts['cmd_list'].extend(module_options.args['init'])

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
                # e.g. TF_VAR_map='{ foo = "bar", baz = "qux" }'
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
        if self.context.no_color:
            tf_cmd.append('-no-color')
        options = TerraformOptions.parse(self.context, self.path,
                                         **self.options.get('options', {}))

        if command == 'destroy':
            tf_cmd.append('-force')
        elif command == 'apply':
            if 'CI' in self.context.env_vars:
                tf_cmd.append('-auto-approve=true')
            else:
                tf_cmd.append('-auto-approve=false')
            tf_cmd.extend(options.args['apply'])
        elif command == 'plan':
            tf_cmd.extend(options.args['plan'])

        workspace_tfvars_file = get_workspace_tfvars_file(self.path,
                                                          self.context.env_name,  # noqa
                                                          self.context.env_region)  # noqa
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
            if options.version:
                tf_bin = TFEnvManager(self.path).install(options.version)
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
                    module_options=options,
                    env_name=self.context.env_name,
                    env_region=self.context.env_region,
                    env_vars=env_vars,
                    no_color=self.context.no_color
                )

                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    [tf_bin,
                     'workspace',
                     'show'] + (['-no-color']
                                if self.context.no_color else []),
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
                        [tf_bin, 'workspace', 'list'] +
                        (['-no-color'] if self.context.no_color else []),
                        env=env_vars
                    ).decode()
                    if re.compile("^[*\\s]\\s%s$" % self.context.env_name,
                                  re.M).search(available_tf_envs):
                        run_module_command(
                            cmd_list=[tf_bin, 'workspace', 'select',
                                      self.context.env_name] +
                            (['-no-color'] if self.context.no_color else []),
                            env_vars=env_vars
                        )
                    else:
                        LOGGER.info("Terraform workspace %s not found; "
                                    "creating it...",
                                    self.context.env_name)
                        run_module_command(
                            cmd_list=[tf_bin, 'workspace', 'new',
                                      self.context.env_name] +
                            (['-no-color'] if self.context.no_color else []),
                            env_vars=env_vars
                        )
                    LOGGER.info('Re-running terraform init after workspace '
                                'change...')
                    run_terraform_init(
                        tf_bin=tf_bin,
                        module_path=self.path,
                        module_options=options,
                        env_name=self.context.env_name,
                        env_region=self.context.env_region,
                        env_vars=env_vars,
                        no_color=self.context.no_color
                    )
                LOGGER.info('Executing "terraform get" to update remote '
                            'modules')
                run_module_command(
                    cmd_list=[tf_bin, 'get', '-update=true'] +
                    (['-no-color'] if self.context.no_color else []),
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


class TerraformOptions(ModuleOptions):
    """Module options for Terraform."""

    def __init__(self, args, backend, version=None):
        """Instantiate class.

        Args:
            args (Union[Dict[str, List[str]], List[str]]): Arguments to append
                to Terraform CLI commands. If providing a list, all arguments
                will be passed to ``terraform apply`` only. Can also be
                provided as a mapping to pass arguments to ``terraform apply``,
                ``terraform init``, and/or ``terraform plan``.
            backend (TerraformBackendConfig): Backend configuration.
            version (Optional[str]): Terraform version.

        """
        super(TerraformOptions, self).__init__()
        self.args = self._parse_args(args)
        self.backend_config = backend
        self.version = version

    @staticmethod
    def _parse_args(args):
        """Parse args option.

        Args:
            args (Union[Dict[str, List[str]], List[str]]): Arguments to append
                to Terraform CLI commands. If providing a list, all arguments
                will be passed to ``terraform apply`` only. Can also be
                provided as a mapping to pass arguments to ``terraform apply``,
                ``terraform init``, and/or ``terraform plan``.

        Returns:
            Dict[str, List[str]]: Arguments seperated by the command they
                should be associated with.

        """
        result = {
            'apply': [],
            'init': [],
            'plan': []
        }

        if isinstance(args, list):
            result['apply'] = args
            return result

        for key in result:
            result[key] = args.get(key, [])

        return result

    @staticmethod
    def resolve_version(context, terraform_version=None, **_):
        """Resolve terraform_version option."""
        if not terraform_version or isinstance(terraform_version, string_types):
            return terraform_version
        if isinstance(terraform_version, dict):
            return terraform_version.get(context.env_name,
                                         terraform_version.get('*'))
        raise TypeError('terraform_version must be of type str or '
                        'Dict[str, str]; got type %s' % type(terraform_version))

    @classmethod
    def parse(cls, context, path=None, **kwargs):  # pylint: disable=arguments-differ
        """Parse the options definition and return an options object.

        Args:
            context (Context): Runway context object.
            path (Optional[str]): Path to the module.

        Keyword Args:
            args (Union[Dict[str, List[str]], List[str]]): Arguments to append
                to Terraform CLI commands. If providing a list, all arguments
                will be passed to ``terraform apply`` only. Can also be
                provided as a mapping to pass arguments to ``terraform apply``,
                ``terraform init``, and/or ``terraform plan``.
            terraform_backend_config (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options.
            terraform_backend_cfn_outputs (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options
                whose values are stored in Cloudformation outputs.
            terraform_backend_ssm_params (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options
                whose values are stored in SSM parameters.
            terraform_version (Optional[Union[Dict[str, str], str]]):
                Version of Terraform to use when processing a module.

        Returns:
            TerraformOptions

        """
        return cls(args=kwargs.get('args', []),
                   backend=TerraformBackendConfig.parse(context, path,
                                                        **kwargs),
                   version=cls.resolve_version(context, **kwargs))


class TerraformBackendConfig(ModuleOptions):
    """Terraform backend configuration module options.

    Attributes:
        OPTIONS (List[str]): A list of option names that are parsed by this
            class.

    """

    OPTIONS = ['terraform_backend_config',
               'terraform_backend_cfn_outputs',
               'terraform_backend_ssm_params']

    def __init__(self, bucket=None, dynamodb_table=None,  # pylint: disable=too-many-arguments
                 filename=None, region=None, key=None, encrypt=None, acl=None, kms_key_id=None,
                 role_arn=None, assume_role_policy=None, external_id=None, session_name=None,
                 workspace_key_prefix=None):
        """Instantiate class.

        Args:
            bucket (Optional[str]): S3 bucket name.
            dynamodb_table (str): DynamoDB table name.
            filename (Optional[str]): .tfvar file name for backend configuration.
            region (Optional[str]): AWS region where both the provided DynamoDB table
                and S3 bucket are located.
            key (Optional[str]): S3 key suffix (filename) for the state.
            workspace_key_prefix (Optional[str]): S3 key prefix to the environment.
            encrypt (Optional[str]): Whether to enable server side encryption of the state file.
            acl (Optional[str]): Canned ACL to be applied to the state file.
            kms_key_id (Optional[str]): KMS Key to use for encrypting the state.
            role_arn (Optional[str]): Role to assume for accessing the state.
            assume_role_policy (Optional[str]): Permissions applied when assuming the role_arn.
            external_id (Optional[str]): External ID to use when assuming the role_arn.
            session_name (Optional[str]): Session name to use when assuming the role_arn.

        """
        super(TerraformBackendConfig, self).__init__()
        self.bucket = bucket
        self.dynamodb_table = dynamodb_table
        self.region = region
        self.key = key
        self.workspace_key_prefix = workspace_key_prefix
        self.encrypt = encrypt
        self.acl = acl
        self.kms_key_id = kms_key_id

        self.role_arn = role_arn
        self.assume_role_policy = assume_role_policy
        self.external_id = external_id
        self.session_name = session_name

        self.filename = filename

    @cached_property
    def init_args(self):
        """Return command line arguments for init."""
        cmd_list = []
        for key in ('acl', 'assume_role_policy', 'bucket', 'dynamodb_table', 'encrypt',
                    'external_id', 'key', 'kms_key_id', 'region', 'role_arn', 'session_name',
                    'workspace_key_prefix'):
            if self.get(key):
                cmd_list.append('-backend-config')
                cmd_list.append(key + '=' + self[key])
            else:
                LOGGER.debug("Skipping terraform backend config option \"%s\" "
                             "-- no value provided", key)
        return cmd_list

    @staticmethod
    def resolve_cfn_outputs(client, **kwargs):
        """Resolve CloudFormation output values.

        Args:
            client (CloudformationClient): Boto3 Cloudformation client.

        Keyword Args:
            bucket (Optional[str]): Cloudformation output containing an S3
                bucket name.
            dynamodb_table (Optional[str]): Cloudformation output containing a
                DynamoDB table name.

        Returns:
            Dict[str, str]: Resolved values from Cloudformation.

        """
        if not kwargs:
            return {}

        result = {}
        for key, val in kwargs.items():
            query = deconstruct(val)
            result[key] = find_cfn_output(query.output_name,
                                          client.describe_stacks(
                                              StackName=query.stack_name
                                          )['Stacks'][0]['Outputs'])
        return result

    @staticmethod
    def resolve_ssm_params(client, **kwargs):
        """Resolve SSM parameters.

        Args:
            client (SSMClient): Boto3 SSM client.

        Keyword Args:
            bucket (Optional[str]): SSM parameter containing an S3 bucket name.
            dynamodb_table (Optional[str]): SSM parameter containing a
                DynamoDB table name.

        Returns:
            Dict[str, str]: Resolved values from SSM.

        """
        dep_msg = ('Use of the "terraform_backend_ssm_params" option has been '
                   'deprecated. The "terraform_backend_config" option with '
                   '"ssm" lookup should be used instead.')
        warnings.warn(dep_msg, DeprecationWarning)
        LOGGER.warning(dep_msg)
        return {key: client.get_parameter(Name=val, WithDecryption=True)
                     ['Parameter']['Value']  # noqa
                for key, val in kwargs.items()}

    @staticmethod
    def gen_backend_tfvars_filenames(environment, region):
        """Generate possible Terraform backend tfvars filenames.

        Args:
            environment (str): Current deploy environment.
            region (str): Current AWS region.

        Returns:
            List[str]: List of possible file names.

        """
        return [
            "backend-%s-%s.tfvars" % (environment, region),
            "backend-%s.tfvars" % environment,
            "backend-%s.tfvars" % region,
            "backend.tfvars"
        ]

    @classmethod
    def get_backend_tfvars_file(cls, path, environment, region):
        """Determine Terraform backend file.

        Args:
            path (str): Path to the module.
            environment (str): Current deploy environment.
            region (str): Current AWS region.

        Returns:
            Optional[str]: Path to a .tfvars file.

        """
        backend_filenames = cls.gen_backend_tfvars_filenames(environment,
                                                             region)
        for name in backend_filenames:
            if os.path.isfile(os.path.join(path, name)):
                return name
        return None

    @classmethod
    def parse(cls, context, path=None, **kwargs):  # pylint: disable=arguments-differ
        """Parse backend options and return an options object.

        Args:
            context (Context): Runway context object.
            path (Optional[str]): Path to the module.

        Keyword Args:
            terraform_backend_config (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options.
            terraform_backend_cfn_outputs (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options
                whose values are stored in Cloudformation outputs.
            terraform_backend_ssm_params (Optional[Dict[str, str]]):
                Mapping of Terraform backend configuration options
                whose values are stored in SSM parameters.

        Returns:
            TerraformBackendConfig

        """
        kwargs = cls.merge_nested_env_dicts({key: val
                                             for key, val in kwargs.items()
                                             if key in cls.OPTIONS},
                                            context.env_name)
        result = kwargs.get('terraform_backend_config', {})

        session = context.get_session(region=result.get('region',
                                                        context.env_region))

        if kwargs.get('terraform_backend_cfn_outputs'):
            result.update(cls.resolve_cfn_outputs(
                client=session.client('cloudformation'),
                **kwargs['terraform_backend_cfn_outputs']))
        if kwargs.get('terraform_backend_ssm_params'):
            result.update(cls.resolve_ssm_params(
                client=session.client('ssm'),
                **kwargs['terraform_backend_ssm_params']))

        if result and not result.get('region'):
            result['region'] = context.env_region

        if path:
            result['filename'] = cls.get_backend_tfvars_file(path,
                                                             context.env_name,
                                                             context.env_region)
        return cls(**result)
