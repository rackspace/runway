"""runway module aka app module."""
from __future__ import print_function

import glob
import logging
import os
import re
import subprocess
import sys

from contextlib import contextmanager

from builtins import input  # pylint: disable=redefined-builtin
from future.utils import viewitems
from send2trash import send2trash

import hcl
import yaml

from .base import Base
# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from ..embedded.stacker.awscli_yamlhelper import yaml_parse as parse_cloudformation_template  # noqa

LOGGER = logging.getLogger('runway')


def make_stacker_cmd_string(args, lib_path):
    """Generate stacker invocation script from command line arg list.

    This is the standard stacker invocation script, with the following changes:
    * Adding our explicit arguments to parse_args (instead of leaving it empty)
    * Overriding sys.argv
    * Adding embedded runway lib directory to sys.path
    """
    return ("import sys;"
            "sys.argv = ['stacker'] + {args};"
            "sys.path.insert(1, '{lib_path}');"
            "from stacker.logger import setup_logging;"
            "from stacker.commands import Stacker;"
            "stacker = Stacker(setup_logging=setup_logging);"
            "args = stacker.parse_args({args});"
            "stacker.configure(args);args.run(args)".format(args=str(args),
                                                            lib_path=lib_path))


def run_module_command(cmd_list, env_vars):
    """Shell out to provisioner command."""
    try:
        subprocess.check_call(cmd_list, env=env_vars)
    except subprocess.CalledProcessError as shelloutexc:
        sys.exit(shelloutexc.returncode)


class Module(Base):  # noqa pylint: disable=too-many-public-methods
    """Module deployment class."""

    def get_sls_config_file(self, stage, region):
        """Determine Serverless config file name."""
        for name in self.gen_sls_config_files(stage, region):
            if os.path.isfile(os.path.join(self.module_root, name)):
                return name
        return "config-%s.json" % stage  # fallback to generic json name

    def get_stacker_env_file(self, environment, region):
        """Determine Stacker environment file name."""
        for name in self.gen_stacker_env_files(environment, region):
            if os.path.isfile(os.path.join(self.module_root, name)):
                return name
        return "%s-%s.env" % (environment, region)  # fallback to env & region

    def get_backend_tfvars_file(self, environment, region):
        """Determine Terraform backend file."""
        backend_filenames = self.gen_backend_tfvars_files(environment, region)
        for name in backend_filenames:
            if os.path.isfile(os.path.join(self.module_root, name)):
                return name
        return backend_filenames[-1]  # file not found; fallback to last item

    def get_workspace_tfvars_file(self, environment, region):
        """Determine Terraform workspace-specific tfvars file name."""
        for name in self.gen_workspace_tfvars_files(environment, region):
            if os.path.isfile(os.path.join(self.module_root, name)):
                return name
        return "%s.tfvars" % environment  # fallback to generic name

    def display_env_source_help(self, environment):
        """Print a helper note about how the environment was determined."""
        if self.environment_override_name in self.env_vars:
            LOGGER.info("Environment \"%s\" was determined from the %s "
                        "environment variable. If this is not correct, update "
                        "the value (or unset it to fall back to the name of "
                        "the current git branch or parent directory).",
                        environment,
                        self.environment_override_name)
        else:
            LOGGER.info("Environment \"%s\" was determined from the current "
                        "git branch or parent directory. If this is not the "
                        "environment name, update the branch/folder name or "
                        "set an override value via the %s environment "
                        "variable",
                        environment,
                        self.environment_override_name)

    def get_blueprint_dir(self):
        """Derive blueprint directory name from app."""
        return os.path.join(
            self.module_root,
            "%s_blueprints" % os.path.basename(self.module_root)
        )

    def templates(self, blueprint_dir=None):
        """Generate CFN templates from troposphere blueprints."""
        if blueprint_dir is None:
            blueprint_dir = os.path.join(
                self.module_root,
                "%s_blueprints" % os.path.basename(self.module_root)
            )
        for filepath in glob.glob(os.path.join(blueprint_dir, '*.py')):
            if os.path.basename(filepath) != '__init__.py':
                cfn_template = subprocess.check_output([filepath])
                try:
                    parsed_cfn_template = parse_cloudformation_template(
                        cfn_template
                    )
                except:  # noqa - bare exception catch is fine here
                    print("Error while checking %s for valid YAML/JSON "
                          "output" % filepath)
                    raise
                output_yaml_file = os.path.join(
                    self.module_root,
                    "%s.yaml" % os.path.splitext(os.path.basename(filepath))[0]
                )
                with open(output_yaml_file, 'w') as yaml_context_file:
                    yaml_context_file.write(
                        yaml.safe_dump(parsed_cfn_template,
                                       default_flow_style=False)
                    )

    def clean(self, blueprint_dir=None):
        """Remove CFN templates generated from troposphere blueprints."""
        if blueprint_dir is None:
            blueprint_dir = os.path.join(
                self.module_root,
                "%s_blueprints" % os.path.basename(self.module_root)
            )
        for filepath in glob.glob(os.path.join(blueprint_dir, '*.py')):
            if os.path.basename(filepath) != '__init__.py':
                fqp = os.path.join(
                    self.module_root,
                    "%s.yaml" % os.path.splitext(os.path.basename(filepath))[0]
                )
                if os.path.isfile(fqp):
                    os.remove(fqp)

    def remove_stale_tf_config(self, backend_tfvars_file):
        """Ensure TF is ready for init.

        If deploying a TF module to multiple regions (or any scenario requiring
        multiple backend configs), switching the backend will cause TF to
        compare the old and new backends. This will frequently cause an access
        error as the creds/role for the new backend won't always have access to
        the old one.

        This method compares the defined & initialized backend configs and
        trashes the terraform directory if they're out of sync.
        """
        terrform_dir = os.path.join(self.module_root, '.terraform')
        tfstate_filepath = os.path.join(terrform_dir, 'terraform.tfstate')
        if os.path.isfile(tfstate_filepath):
            LOGGER.debug('Comparing previous & desired Terraform backend '
                         'configs')
            with open(tfstate_filepath, 'r') as fco:
                state_config = hcl.load(fco)

            if state_config.get('backend') and state_config['backend'].get('config'):  # noqa
                backend_tfvars_filepath = os.path.join(self.module_root,
                                                       backend_tfvars_file)
                with open(backend_tfvars_filepath, 'r') as fco:
                    backend_config = hcl.load(fco)
                if any(state_config['backend']['config'][key] != value for (key, value) in viewitems(backend_config)):  # noqa pylint: disable=line-too-long
                    LOGGER.info("Desired and previously initialized TF "
                                "backend config is out of sync; trashing "
                                "local TF state directory %s",
                                terrform_dir)
                    send2trash(terrform_dir)

    def run_serverless(self, environment, region, command='deploy'):
        """Run Serverless."""
        response = {'skipped_configs': False}
        sls_opts = [command]

        if not self.which('npm'):
            LOGGER.error('"npm" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if 'CI' in self.env_vars and command != 'remove':
            sls_opts.append('--conceal')  # Hide secrets from serverless output

        if 'DEBUG' in self.env_vars:
            sls_opts.append('-v')  # Increase logging if requested

        sls_opts.extend(['-r', region])
        sls_opts.extend(['--stage', environment])
        sls_env_file = self.get_sls_config_file(environment, region)

        if self.which('npx'):
            # Use npx if available (npm v5.2+)
            LOGGER.debug('Using npx to invoke sls.')
            # The nested sls-through-npx-via-subprocess command invocation
            # requires this redundant quoting
            sls_cmd = ['npx', '-c', "''sls %s''" % ' '.join(sls_opts)]
        else:
            LOGGER.debug('npx not found; falling back invoking sls shell '
                         'script directly.')
            sls_cmd = [
                os.path.join(self.module_root,
                             'node_modules',
                             '.bin',
                             'sls')
            ] + sls_opts

        if os.path.isfile(os.path.join(self.module_root, sls_env_file)):
            if os.path.isfile(os.path.join(self.module_root, 'package.json')):
                with self.change_dir(self.module_root):
                    if not self.deploy_opts.get('skip-npm-ci'):
                        # Use npm ci if available (npm v5.7+)
                        if self.use_npm_ci():
                            LOGGER.info("Running npm ci on %s...",
                                        os.path.basename(self.module_root))
                            subprocess.check_call(['npm', 'ci'])
                        else:
                            LOGGER.info("Running npm install on %s...",
                                        os.path.basename(self.module_root))
                            subprocess.check_call(['npm', 'install'])
                    LOGGER.info("Running sls %s on %s (\"%s\")",
                                command,
                                os.path.basename(self.module_root),
                                # Strip out redundant npx quotes not needed
                                # when executing the command directly
                                " ".join(sls_cmd).replace('\'\'', '\''))
                    run_module_command(cmd_list=sls_cmd,
                                       env_vars=self.env_vars)
            else:
                LOGGER.warn(
                    "Skipping serverless %s of %s; no \"package.json\" "
                    "file was found (need a package file specifying "
                    "serverless in devDependencies)",
                    command,
                    os.path.basename(self.module_root))
        else:
            response['skipped_configs'] = True
            LOGGER.info(
                "Skipping serverless %s of %s; no config file for "
                "this stage/region found (looking for one of \"%s\")",
                command,
                os.path.basename(self.module_root),
                ', '.join(self.gen_sls_config_files(environment, region)))
        return response

    def run_terraform(self, environment, region, command='plan'):  # noqa pylint: disable=too-many-branches,too-many-statements
        """Run Terraform."""
        response = {'skipped_configs': False}
        tf_cmd = ['terraform', command]

        if not self.which('terraform'):
            LOGGER.error('"terraform" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if command == 'destroy':
            tf_cmd.append('-force')
        elif command == 'apply':
            if 'CI' in self.env_vars:
                tf_cmd.append('-auto-approve=true')
            else:
                tf_cmd.append('-auto-approve=false')

        workspace_tfvars_file = self.get_workspace_tfvars_file(environment,
                                                               region)
        backend_tfvars_file = self.get_backend_tfvars_file(environment,
                                                           region)
        tf_cmd.append("-var-file=%s" % workspace_tfvars_file)

        backend_tfvar_present = os.path.isfile(
            os.path.join(self.module_root, backend_tfvars_file)
        )
        workspace_tfvar_present = os.path.isfile(
            os.path.join(self.module_root, workspace_tfvars_file)
        )
        if workspace_tfvar_present:
            LOGGER.info("Preparing to run terraform %s on %s...",
                        command,
                        os.path.basename(self.module_root))
            if os.path.isfile(os.path.join(self.module_root,
                                           '.terraform-version')):
                self.run_tfenv_install()
            with self.change_dir(self.module_root):
                if not os.path.isdir(os.path.join(self.module_root,
                                                  '.terraform')):
                    LOGGER.info('.terraform directory missing; running '
                                '"terraform init"...')
                    init_cmd = ['terraform', 'init']
                    if backend_tfvar_present:
                        LOGGER.info('Using backend config file %s',
                                    backend_tfvars_file)
                        self.remove_stale_tf_config(backend_tfvars_file)
                        subprocess.check_call(
                            init_cmd + ['-backend-config=%s' % backend_tfvars_file],  # noqa
                            env=self.env_vars
                        )
                    else:
                        LOGGER.info(
                            "No backend tfvars file found -- looking for one "
                            "of \"%s\" (proceeding with bare 'terraform "
                            "init')",
                            ', '.join(self.gen_backend_tfvars_files(
                                environment,
                                region)))
                        subprocess.check_call(init_cmd, env=self.env_vars)
                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    ['terraform',
                     'workspace',
                     'show'],
                    env=self.env_vars
                ).strip()
                if current_tf_workspace != environment:
                    LOGGER.info("Terraform workspace current set to %s; "
                                "switching to %s...",
                                current_tf_workspace,
                                environment)
                    LOGGER.debug('Checking available Terraform '
                                 'workspaces...')
                    available_tf_envs = subprocess.check_output(
                        ['terraform', 'workspace', 'list'],
                        env=self.env_vars
                    )
                    if re.compile("^[*\\s]\\s%s$" % environment,
                                  re.M).search(available_tf_envs):
                        subprocess.check_call(
                            ['terraform',
                             'workspace',
                             'select',
                             environment],
                            env=self.env_vars)
                    else:
                        LOGGER.info("Terraform workspace %s not found; "
                                    "creating it...",
                                    environment)
                        subprocess.check_call(
                            ['terraform',
                             'workspace',
                             'new',
                             environment],
                            env=self.env_vars)
                if 'SKIP_TF_GET' not in self.env_vars:
                    LOGGER.info('Executing "terraform get" to update remote '
                                'modules')
                    subprocess.check_call(['terraform', 'get', '-update=true'],
                                          env=self.env_vars)
                else:
                    LOGGER.info('Skipping "terraform get" due to '
                                '"SKIP_TF_GET" environment variable...')
                LOGGER.info("Running Terraform %s on %s (\"%s\")",
                            command,
                            os.path.basename(self.module_root),
                            " ".join(tf_cmd))
                run_module_command(cmd_list=tf_cmd, env_vars=self.env_vars)
        else:
            response['skipped_configs'] = True
            LOGGER.info("Skipping Terraform %s of %s",
                        command,
                        os.path.basename(self.module_root))
            LOGGER.info(
                "(no tfvars file for this environment/region found -- looking "
                "for one of \"%s\")",
                ', '.join(self.gen_workspace_tfvars_files(
                    environment,
                    region)))
        return response

    def run_stacker(self, environment, region, command='diff'):
        """Run Stacker."""
        response = {'skipped_configs': False}
        stacker_cmd = [command, "--region=%s" % region]

        if command == 'destroy':
            stacker_cmd.append('--force')
        elif command == 'build':
            if 'CI' in self.env_vars:
                stacker_cmd.append('--recreate-failed')
            else:
                stacker_cmd.append('--interactive')

        if 'DEBUG' in self.env_vars:
            stacker_cmd.append('--verbose')  # Increase logging if requested

        stacker_env_file = self.get_stacker_env_file(environment, region)
        stacker_cmd.append(stacker_env_file)

        with self.change_dir(self.module_root):
            # Iterate through any stacker yaml configs to deploy them in order
            # or destroy them in reverse order
            for _root, _dirs, files in os.walk(self.module_root):
                for name in (
                        reversed(sorted(files))
                        if command == 'destroy'
                        else sorted(files)):
                    if name == 'runway.yml' or name.startswith('.'):
                        # Hidden files (e.g. .gitlab-ci.yml) or runway configs
                        # definitely aren't stacker config files
                        continue
                    if os.path.splitext(name)[1] in ['.yaml', '.yml']:
                        if not os.path.isfile(os.path.join(self.module_root,
                                                           stacker_env_file)):
                            response['skipped_configs'] = True
                            LOGGER.info(
                                "Skipping stacker %s of %s; no environment "
                                "file found for this environment/region "
                                "(looking for one of \"%s\")",
                                command,
                                name,
                                ', '.join(
                                    self.gen_stacker_env_files(environment,
                                                               region))
                            )
                            continue
                        self.ensure_stacker_compat_config(
                            os.path.join(self.module_root, name)
                        )
                        LOGGER.info("Running stacker %s on %s",
                                    command,
                                    name)
                        stacker_cmd_str = make_stacker_cmd_string(
                            stacker_cmd + [name],
                            self.embedded_lib_path
                        )
                        stacker_cmd_list = [sys.executable, '-c']
                        LOGGER.debug(
                            "Stacker command being executed: %s \"%s\"",
                            ' '.join(stacker_cmd_list),
                            stacker_cmd_str
                        )
                        run_module_command(
                            cmd_list=stacker_cmd_list + [stacker_cmd_str],
                            env_vars=self.env_vars
                        )
                break  # only need top level files
        return response

    def determine_module_type(self):
        """Determine type of module."""
        module_type = ''
        # First check directory name for type-indicating suffix
        if os.path.basename(self.module_root).endswith('.sls'):
            module_type = 'serverless'
        elif os.path.basename(self.module_root).endswith('.tf'):
            module_type = 'terraform'
        elif os.path.basename(self.module_root).endswith('.cfn'):
            module_type = 'stacker'
        # Fallback to autodetection
        if module_type == '':
            if os.path.isfile(os.path.join(self.module_root,
                                           'serverless.yml')):
                module_type = 'serverless'
            elif glob.glob(os.path.join(self.module_root, '*.tf')):
                module_type = 'terraform'
            elif glob.glob(os.path.join(self.module_root, '*.env')):
                module_type = 'stacker'
        if module_type == '':
            LOGGER.error('No valid deployment configurations found for %s',
                         os.path.basename(self.module_root))
            sys.exit(1)
        return module_type

    def get_and_update_region(self):
        """Find AWS region, prompting if necessary."""
        if 'AWS_DEFAULT_REGION' not in self.env_vars:
            aws_region = input("Please enter the AWS region: ")
            self.update_env_vars({'AWS_DEFAULT_REGION': aws_region,
                                  'AWS_REGION': aws_region})
        return self.env_vars['AWS_DEFAULT_REGION']

    def plan(self):
        """Determine what will happen on a deploy run."""
        environment = self.environment_name
        aws_region = self.get_and_update_region()
        LOGGER.info("Planning deployment to %s environment in region %s...",
                    environment,
                    aws_region)

        module_type = self.determine_module_type()
        plan_result = {}
        if module_type == 'serverless':
            LOGGER.info('Planning not currently supported for Serverless')
        elif module_type == 'terraform':
            plan_result = self.run_terraform(
                environment=environment,
                region=aws_region,
                command='plan'
            )
        elif module_type == 'stacker':
            plan_result = self.run_stacker(
                environment=environment,
                region=aws_region,
                command='diff'
            )
        if ('skipped_configs' in plan_result and
                plan_result['skipped_configs']):
            LOGGER.info(self.display_env_source_help(environment))

    def deploy(self):
        """Deploy apps/code."""
        environment = self.environment_name
        aws_region = self.get_and_update_region()
        LOGGER.info("Deploying to %s environment in region %s...",
                    environment,
                    aws_region)

        module_type = self.determine_module_type()
        deploy_result = {}
        if module_type == 'serverless':
            deploy_result = self.run_serverless(
                environment=environment,
                region=aws_region,
                command='deploy'
            )
        elif module_type == 'terraform':
            deploy_result = self.run_terraform(
                environment=environment,
                region=aws_region,
                command='apply'
            )
        elif module_type == 'stacker':
            deploy_result = self.run_stacker(
                environment=environment,
                region=aws_region,
                command='build'
            )
        if ('skipped_configs' in deploy_result and
                deploy_result['skipped_configs']):
            LOGGER.info(self.display_env_source_help(environment))

    def destroy(self):
        """Destroy apps/code."""
        environment = self.environment_name
        aws_region = self.get_and_update_region()
        LOGGER.info("Removing deployment in %s environment in region %s...",
                    environment,
                    aws_region)

        module_type = self.determine_module_type()
        deploy_result = {}
        if module_type == 'serverless':
            deploy_result = self.run_serverless(
                environment=environment,
                region=aws_region,
                command='remove'
            )
        elif module_type == 'terraform':
            deploy_result = self.run_terraform(
                environment=environment,
                region=aws_region,
                command='destroy'
            )
        elif module_type == 'stacker':
            deploy_result = self.run_stacker(
                environment=environment,
                region=aws_region,
                command='destroy'
            )
        if ('skipped_configs' in deploy_result and
                deploy_result['skipped_configs']):
            LOGGER.info(self.display_env_source_help(environment))

    def use_npm_ci(self):
        """Return true if npm ci should be used in lieu of npm install."""
        # https://docs.npmjs.com/cli/ci#description
        with open(os.devnull, 'w') as fnull:
            if ((os.path.isfile(os.path.join(self.module_root,
                                             'package-lock.json')) or
                 os.path.isfile(os.path.join(self.module_root,
                                             'npm-shrinkwrap.json'))) and
                    subprocess.call(
                        ['npm', 'ci', '-h'],
                        stdout=fnull,
                        stderr=subprocess.STDOUT
                    ) == 0):
                return True
        return False

    def run_tfenv_install(self):
        """Ensure appropriate Terraform version is installed."""
        if self.which('tfenv') is None:
            LOGGER.error('"tfenv" not found (and a Terraform version is '
                         'specified in .terraform-version). Please install '
                         'tfenv.')
            sys.exit(1)
        with self.change_dir(self.module_root):
            subprocess.check_call(['tfenv', 'install'], env=self.env_vars)

    @contextmanager
    def override_env_vars(self, env_vars=None):
        """Temporarily use the class env_vars as the os env vars."""
        if env_vars is None:
            env_vars = self.env_vars
        orig_env_vars = os.environ
        os.environ = env_vars
        try:
            yield
        finally:
            os.environ = orig_env_vars

    def execute(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError('You must implement the execute() method '
                                  'yourself!')

    @staticmethod
    def ensure_stacker_compat_config(config_filename):
        """Ensure config file can be loaded by Stacker."""
        try:
            with open(config_filename, 'r') as stream:
                yaml.load(stream)
        except yaml.constructor.ConstructorError as yaml_error:
            if yaml_error.problem.startswith(
                    'could not determine a constructor for the tag \'!'):
                LOGGER.error('"%s" appears to be a CloudFormation template, '
                             'but is located in the top level of a module '
                             'alongside the CloudFormation config files (i.e. '
                             'the file or files indicating the stack names & '
                             'parameters). Please move the template to a '
                             'subdirectory.',
                             config_filename)
                sys.exit(1)

    @staticmethod
    def gen_backend_tfvars_files(environment, region):
        """Generate possible Terraform backend tfvars filenames."""
        return [
            "backend-%s-%s.tfvars" % (environment, region),
            "backend-%s.tfvars" % environment,
            "backend-%s.tfvars" % region,
            "backend.tfvars"
        ]

    @staticmethod
    def gen_workspace_tfvars_files(environment, region):
        """Generate possible Terraform workspace tfvars filenames."""
        return [
            # Give preference to explicit environment-region files
            "%s-%s.tfvars" % (environment, region),
            # Fallback to environment name only
            "%s.tfvars" % environment
        ]

    @staticmethod
    def gen_sls_config_files(stage, region):
        """Generate possible SLS config files names."""
        names = []
        for ext in ['yml', 'json']:
            # Give preference to explicit stage-region files
            names.append(
                os.path.join('env',
                             "%s-%s.%s" % (stage, region, ext))
            )
            names.append("config-%s-%s.%s" % (stage, region, ext))
            # Fallback to stage name only
            names.append(
                os.path.join('env',
                             "%s.%s" % (stage, ext))
            )
            names.append("config-%s.%s" % (stage, ext))
        return names

    @staticmethod
    def gen_stacker_env_files(environment, region):
        """Generate possible Stacker environment filenames."""
        return [
            # Give preference to explicit environment-region files
            "%s-%s.env" % (environment, region),
            # Fallback to environment name only
            "%s.env" % environment
        ]
