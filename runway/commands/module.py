"""runway module aka app module."""
from __future__ import print_function

import glob
import logging
import os
import re
import subprocess
import sys

from builtins import input  # pylint: disable=redefined-builtin

import yaml

from .base import Base
# from stacker.util import parse_cloudformation_template
# parse_cloudformation_template wraps yaml_parse; it would be better to call it
# from util but that would require sys.path shenanigans here
from ..embedded.stacker.awscli_yamlhelper import yaml_parse as parse_cloudformation_template  # noqa

logging.basicConfig(level=logging.INFO)
# logging.getLogger('botocore').setLevel(logging.ERROR)  # their info is spammy
LOGGER = logging.getLogger('runway')


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
        for name in self.gen_backend_tfvars_files(environment, region):
            if os.path.isfile(os.path.join(self.module_root, name)):
                return name
        return "backend.tfvars"  # fallback to generic name

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

    def deploy_serverless(self, environment, region):
        """Deploy Serverless app."""
        response = {'skipped_configs': False}
        sls_cmd = ['npm', 'run-script', 'sls', '--', 'deploy']

        if not self.which('npm'):
            LOGGER.error('"npm" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if 'CI' in self.env_vars:
            sls_cmd.append('--conceal')  # Hide secrets from serverless output

        if 'DEBUG' in self.env_vars:
            sls_cmd.append('-v')  # Increase logging if requested

        sls_cmd.extend(['-r', region])
        sls_env_file = self.get_sls_config_file(environment, region)
        sls_cmd.extend(['--stage', environment])

        if os.path.isfile(os.path.join(self.module_root, sls_env_file)):
            if os.path.isfile(os.path.join(self.module_root, 'package.json')):
                with self.change_dir(self.module_root):
                    # Use npm ci if available (npm v5.7+)
                    if self.use_npm_ci():
                        LOGGER.info("Running npm ci on %s...",
                                    os.path.basename(self.module_root))
                        subprocess.check_call(['npm', 'ci'])
                    else:
                        LOGGER.info("Running npm install on %s...",
                                    os.path.basename(self.module_root))
                        subprocess.check_call(['npm', 'install'])
                    LOGGER.info("Running sls build on %s (\"%s\")",
                                os.path.basename(self.module_root),
                                " ".join(sls_cmd))
                    subprocess.check_call(sls_cmd)
            else:
                LOGGER.warn(
                    "Skipping serverless deploy of %s; no \"package.json\" "
                    "file was found (need a package file specifying "
                    "serverless in devDependencies & a \"deploy\" script "
                    "invoking \"sls deploy\")",
                    os.path.basename(self.module_root))
        else:
            response['skipped_configs'] = True
            LOGGER.info(
                "Skipping serverless deploy of %s; no config file for "
                "this stage/region found (looking for one of \"%s\")",
                os.path.basename(self.module_root),
                ', '.join(self.gen_sls_config_files(environment, region)))
        return response

    def run_terraform(self, environment, region, command='plan'):  # noqa pylint: disable=too-many-branches
        """Deploy Terraform app."""
        response = {'skipped_configs': False}
        tf_cmd = ['terraform', command]

        if not self.which('terraform'):
            LOGGER.error('"terraform" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if command != 'plan':
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
            with self.change_dir(self.module_root):
                if not os.path.isdir(os.path.join(self.module_root,
                                                  '.terraform')):
                    LOGGER.info('.terraform directory missing; running '
                                '"terraform init"...')
                    init_cmd = ['terraform', 'init']
                    if backend_tfvar_present:
                        LOGGER.info('Using backend config file %s',
                                    backend_tfvars_file)
                        subprocess.check_call(
                            init_cmd + ['-backend-config=%s' % backend_tfvars_file]  # noqa
                        )
                    else:
                        LOGGER.info(
                            "No backend tfvars file found -- looking for one "
                            "of \"%s\" (proceeding with bare 'terraform "
                            "init')",
                            ', '.join(self.gen_backend_tfvars_files(
                                environment,
                                region)))
                        subprocess.check_call(init_cmd)
                LOGGER.debug('Checking current Terraform workspace...')
                current_tf_workspace = subprocess.check_output(
                    ['terraform',
                     'workspace',
                     'show']
                ).strip()
                if current_tf_workspace != environment:
                    LOGGER.info("Terraform workspace current set to %s; "
                                "switching to %s...",
                                current_tf_workspace,
                                environment)
                    LOGGER.debug('Checking available Terraform '
                                 'workspaces...')
                    available_tf_envs = subprocess.check_output(['terraform',
                                                                 'workspace',
                                                                 'list'])
                    if re.compile("^[*\\s]\\s%s$" % environment,
                                  re.M).search(available_tf_envs):
                        subprocess.check_call(
                            ['terraform',
                             'workspace',
                             'select',
                             environment])
                    else:
                        LOGGER.info("Terraform workspace %s not found; "
                                    "creating it...",
                                    environment)
                        subprocess.check_call(
                            ['terraform',
                             'workspace',
                             'new',
                             environment])
                if 'SKIP_TF_GET' not in self.env_vars:
                    LOGGER.info('Executing "terraform get" to update remote '
                                'modules')
                    subprocess.check_call(['terraform', 'get', '-update=true'])
                else:
                    LOGGER.info('Skipping "terraform get" due to '
                                '"SKIP_TF_GET" environment variable...')
                LOGGER.info("Running Terraform %s on %s (\"%s\")",
                            command,
                            os.path.basename(self.module_root),
                            " ".join(tf_cmd))
                subprocess.check_call(tf_cmd)
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

        if command != 'diff':
            if 'CI' in self.env_vars:
                stacker_cmd.append('--recreate-failed')
            else:
                stacker_cmd.append('--interactive')

        if 'DEBUG' in self.env_vars:
            stacker_cmd.append('--verbose')  # Increase logging if requested

        stacker_env_file = self.get_stacker_env_file(environment, region)
        stacker_env_file = "%s-%s.env" % (environment, region)
        stacker_cmd.append(stacker_env_file)

        with self.change_dir(self.module_root):
            # Iterate through any stacker yaml configs to deploy them in order
            for _root, _dirs, files in os.walk(self.module_root):
                for name in sorted(files):
                    if name == 'runway.yml':
                        continue
                    file_extension = os.path.splitext(name)[1]
                    if file_extension in ['.yaml', '.yml']:
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
                        # Need to override command line arguments (even when
                        # running stacker directly like this) because its
                        # hooks may call util.get_config_directory() which
                        # checks the command line arguments directly
                        with self.override_sysargv(['stacker'] + stacker_cmd):
                            # Ensure any blueprints use our embedded version of
                            # stacker
                            with self.use_embedded_pkgs():
                                with self.turn_down_stacker_logging(command):
                                    from ..embedded.stacker.commands import Stacker  # noqa
                                    stacker = Stacker()
                                    args = stacker.parse_args(
                                        stacker_cmd + [name]
                                    )
                                    stacker.configure(args)
                                    args.run(args)
                break  # only need top level files
        return response

    def determine_module_type(self):
        """Determine type of module."""
        # First check directory name for type-indicating suffix
        if os.path.basename(self.module_root).endswith('.sls'):
            return 'serverless'
        elif os.path.basename(self.module_root).endswith('.tf'):
            return 'terraform'
        elif os.path.basename(self.module_root).endswith('.cfn'):
            return 'stacker'
        # Fallback to autodetection
        if os.path.isfile(os.path.join(self.module_root, 'serverless.yml')):
            return 'serverless'
        elif glob.glob(os.path.join(self.module_root, '*.tf')):
            return 'terraform'
        elif glob.glob(os.path.join(self.module_root, '*.env')):
            return 'stacker'
        else:
            LOGGER.error('No valid deployment configurations found for %s',
                         os.path.basename(self.module_root))
            sys.exit(1)

    def get_and_update_region(self):
        """Find AWS region, prompting if necessary."""
        if 'AWS_DEFAULT_REGION' not in self.env_vars:
            aws_region = input("Please enter the AWS region: ")
            self.update_env_vars({'AWS_DEFAULT_REGION': aws_region})
        return self.env_vars['AWS_DEFAULT_REGION']

    def plan(self):
        """Determine what will happen on a deploy run."""
        environment = self.get_env()
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
        environment = self.get_env()
        aws_region = self.get_and_update_region()
        LOGGER.info("Deploying to %s environment in region %s...",
                    environment,
                    aws_region)

        module_type = self.determine_module_type()
        deploy_result = {}
        if module_type == 'serverless':
            deploy_result = self.deploy_serverless(
                environment=environment,
                region=aws_region
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

    def get_env(self, directory=None):
        """Determine environment name."""
        if self.environment_override_name in self.env_vars:
            return self.env_vars[self.environment_override_name]

        if self.runway_config.get('ignore_git_branch', False):
            LOGGER.info('Skipping environment lookup from current git branch '
                        '("ignore_git_branch" is set to true in the runway '
                        'config)')
        else:
            # These are not located with the top imports because they throw an
            # error if git isn't installed
            from git import Repo as GitRepo
            from git.exc import InvalidGitRepositoryError

            if directory is None:
                directory = self.module_root
            try:
                b_name = GitRepo(
                    directory,
                    search_parent_directories=True
                ).active_branch.name
                LOGGER.info('Deriving environment name from git branch %s...',
                            b_name)
                return self.get_env_from_branch(b_name)
            except InvalidGitRepositoryError:
                pass
        LOGGER.info('Deriving environment name from directory %s...',
                    self.env_root)
        return self.get_env_from_directory(os.path.basename(self.env_root))

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
    def get_env_from_branch(branch_name):
        """Determine environment name from git branch name."""
        if branch_name.startswith('ENV-'):
            return branch_name[4:]
        elif branch_name == 'master':
            LOGGER.info('Translating git branch "master" to environment '
                        '"common"')
            return 'common'
        return branch_name

    @staticmethod
    def get_env_from_directory(directory_name):
        """Determine environment name from directory name."""
        if directory_name.startswith('ENV-'):
            return directory_name[4:]
        return directory_name

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
            names.append("config-%s-%s.%s" % (stage, region, ext))
            # Fallback to stage name only
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
