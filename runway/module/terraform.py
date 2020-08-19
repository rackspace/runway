"""Terraform module."""
import json
import logging
import re
import subprocess
import sys

import hcl
import six
from send2trash import send2trash

from .._logging import PrefixAdaptor
from ..cfngin.lookups.handlers.output import deconstruct
from ..env_mgr.tfenv import TFEnvManager
from ..util import DOC_SITE, cached_property, find_cfn_output, which
from . import ModuleOptions, RunwayModule, run_module_command

if sys.version_info[0] > 2:  # TODO remove after droping python 2
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)


def gen_workspace_tfvars_files(environment, region):
    """Generate possible Terraform workspace tfvars filenames."""
    return [
        # Give preference to explicit environment-region files
        "%s-%s.tfvars" % (environment, region),
        # Fallback to environment name only
        "%s.tfvars" % environment,
    ]


def update_env_vars_with_tf_var_values(os_env_vars, tf_vars):
    """Return os_env_vars with TF_VAR_ values for each tf_var."""
    # https://www.terraform.io/docs/commands/environment-variables.html#tf_var_name
    for (key, val) in tf_vars.items():
        if isinstance(val, dict):
            os_env_vars["TF_VAR_%s" % key] = "{ %s }" % str(
                # e.g. TF_VAR_map='{ foo = "bar", baz = "qux" }'
                ", ".join(
                    [
                        nestedkey + ' = "' + nestedval + '"'
                        for (nestedkey, nestedval) in val.items()
                    ]
                )
            )
        elif isinstance(val, list):
            os_env_vars["TF_VAR_%s" % key] = json.dumps(val)
        else:
            os_env_vars["TF_VAR_%s" % key] = val
    return os_env_vars


class Terraform(RunwayModule):
    """Terraform Runway Module."""

    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (Union[str, Path]): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        options = options or {}
        super(Terraform, self).__init__(context.copy(), path, options)
        del self.options  # remove the attr set by the parent class

        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)
        self.path = path if isinstance(self.path, Path) else Path(self.path)

        self._raw_path = Path(options.pop("path")) if options.get("path") else None
        self.environments = options.pop("environments", {})
        self.options = TerraformOptions.parse(
            context, self.path, **options.pop("options", {})
        )
        self.parameters = options.pop("parameters", {})
        self.required_workspace = self.options.workspace or self.context.env.name

        for k, v in options.items():
            setattr(self, k, v)

    @cached_property
    def auto_tfvars(self):
        """Return auto.tfvars file if one is being used."""
        file_path = self.path / "runway-parameters.auto.tfvars.json"
        if self.parameters and self.options.write_auto_tfvars:
            try:
                if self.tfenv.current_version:
                    current_version = tuple(
                        int(i) for i in self.tfenv.current_version.split(".")
                    )
                    if current_version < (0, 10):
                        self.logger.warning(
                            "Terraform version does not support the use of "
                            "*.auto.tfvars; some variables may be missing"
                        )
            except Exception:  # pylint: disable=broad-except
                self.logger.debug("unable to parse current version", exc_info=True)
            file_path.write_text(six.u(json.dumps(self.parameters, indent=4)))
        return file_path

    @cached_property
    def current_workspace(self):
        """Wrap "terraform_workspace_show" to cache the value.

        Returns:
            str: The currently active Terraform workspace.

        """
        return self.terraform_workspace_show()

    @cached_property
    def env_file(self):
        """Find the environment file for the module.

        Returns:
            Path: Path object for the environment file that was found.

        """
        result = []
        for name in gen_workspace_tfvars_files(
            self.context.env.name, self.context.env.aws_region
        ):
            test_path = self.path / name
            if test_path.is_file():
                result.append("-var-file=" + test_path.name)
                break  # stop looking if one is found
        return result

    @property
    def skip(self):
        """Determine if the module should be skipped.

        Returns:
            bool: To skip, or not to skip, that is the question.

        """
        if self.parameters or self.env_file:
            return False
        self.logger.info(
            "skipped; tfvars file for this environmet/region not found "
            "and no parameters provided -- looking for one of: %s",
            ", ".join(
                gen_workspace_tfvars_files(
                    self.context.env.name, self.context.env.aws_region
                )
            ),
        )
        return True

    @cached_property
    def tfenv(self):
        """Terraform environmet manager."""
        return TFEnvManager(self.path)

    @cached_property
    def tf_bin(self):
        """Path to Terraform binary."""
        try:
            return self.tfenv.install(self.options.version)
        except ValueError:
            self.logger.debug("terraform install failed", exc_info=True)
            self.logger.verbose(
                "terraform version not specified; resorting to global install"
            )
            if which("terraform"):
                return "terraform"
        self.logger.error(
            "terraform not available and a version to install not specified"
        )
        self.logger.error(
            "learn how to use Runway to manage Terraform versions at "
            "%s/page/terraform/advanced_features.html#version-management",
            DOC_SITE,
        )
        sys.exit(1)

    def cleanup_dot_terraform(self):
        """Remove .terraform excluding the plugins directly.

        This step is crucial for allowing Runway to deploy to multiple regions
        or deploy environments without promping the user for input.

        The plugins directory is retained to improve performance when they
        are used by subsequent runs.

        """
        dot_terraform = self.path / ".terraform"
        if not dot_terraform.is_dir():
            self.logger.debug(".terraform directory does not exist; skipped cleanup")
            return

        self.logger.verbose(
            ".terraform directory exists from a previous run; "
            "removing some of its contents"
        )
        for child in dot_terraform.iterdir():
            if child.name == "plugins" and child.is_dir():
                self.logger.debug("directory retained: %s", child)
                continue
            self.logger.debug("removing: %s", child)
            send2trash(str(child))  # TODO remove str when dropping python 2

    def gen_command(self, command, args_list=None):
        """Generate Terraform command."""
        if isinstance(command, (list, tuple)):
            cmd = [self.tf_bin] + command
        else:
            cmd = [self.tf_bin, command]
        cmd.extend(args_list or [])
        if self.context.no_color:
            cmd.append("-no-color")
        return cmd

    def handle_backend(self):
        """Handle backend configuration.

        This needs to be run before "skip" is assessed or env_file/auto_tfvars
        is used in case their behavior needs to be altered.

        """
        if not self.tfenv.backend["type"]:
            self.logger.info(
                "unable to determine backend for module; no special handling"
                "will be applied"
            )
            return
        handler = "_%s_backend_handler" % self.tfenv.backend["type"]
        if hasattr(self, handler):
            self.tfenv.backend["config"].update(
                self.options.backend_config.get_full_configuration()
            )
            self.logger.debug(
                "full backend config: %s", json.dumps(self.tfenv.backend["config"])
            )
            self.logger.verbose(
                "handling use of backend config: %s", self.tfenv.backend["type"]
            )
            self["_%s_backend_handler" % self.tfenv.backend["type"]]()
        else:
            self.logger.verbose(
                'backed "%s" does not require special handling',
                self.tfenv.backend["type"],
                exc_info=True,
            )

    def _remote_backend_handler(self):
        """Handle special setting required for using a remote backend."""
        if not self.tfenv.backend["config"].get("workspaces"):
            self.logger.warning(
                '"workspaces" not defined in backend config; unable to '
                "apply appropriate handling -- processing may fail"
            )
            return

        self.logger.verbose(
            "forcing parameters to be written to runway-parameters.auto.tfvars.json"
        )
        # this is because variables cannot be added inline or via environment
        # variables when using a remote backend
        self.options.write_auto_tfvars = True

        if self.tfenv.backend["config"]["workspaces"].get("prefix"):
            self.logger.verbose(
                "handling use of backend config: remote.workspaces.prefix"
            )
            self.context.env.vars.update({"TF_WORKSPACE": self.context.env.name})
            self.logger.verbose(
                'set environment variable "TF_WORKSPACE" to avoid prompt '
                "during init by pre-selecting an appropriate workspace"
            )

        if self.tfenv.backend["config"]["workspaces"].get("name"):
            self.logger.verbose(
                "handling use of backend config: remote.workspaces.name"
            )
            # this can't be set or it will cause errors
            self.context.env.vars.pop("TF_WORKSPACE", None)
            self.required_workspace = "default"
            self.logger.info(
                'forcing use of static workspace "default"; '
                'required for use of "backend.remote.workspaces.name"'
            )

    def handle_parameters(self):
        """Handle parameters.

        Either updating environment variables or writing to a file.

        """
        if self.auto_tfvars.exists():
            return

        self.context.env.vars = update_env_vars_with_tf_var_values(
            self.context.env.vars, self.parameters
        )

    def terraform_apply(self):
        """Execute ``terraform apply`` command.

        https://www.terraform.io/docs/commands/apply.html

        """
        args_list = self.env_file + self.options.args["apply"]
        if self.context.env.ci:
            args_list.append("-auto-approve=true")
        else:
            args_list.append("-auto-approve=false")
        run_module_command(
            self.gen_command("apply", args_list),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )

    def terraform_destroy(self):
        """Execute ``terraform destroy`` command.

        https://www.terraform.io/docs/commands/destroy.html

        """
        run_module_command(
            self.gen_command("destroy", ["-force"] + self.env_file),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )

    def terraform_get(self):
        """Execute ``terraform get`` command.

        https://www.terraform.io/docs/commands/get.html

        """
        self.logger.info("downloading and updating Terraform modules")
        run_module_command(
            self.gen_command("get", ["-update=true"]),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )

    def terraform_init(self):
        """Execute ``terraform init`` command.

        https://www.terraform.io/docs/commands/init.html

        """
        cmd = self.gen_command(
            "init",
            ["-reconfigure"]
            + self.options.backend_config.init_args
            + self.options.args["init"],
        )
        try:
            run_module_command(
                cmd,
                env_vars=self.context.env.vars,
                exit_on_error=False,
                logger=self.logger,
            )
        except subprocess.CalledProcessError as shelloutexc:
            # cleaner output by not letting the exception raise
            sys.exit(shelloutexc.returncode)

    def terraform_plan(self):
        """Execute ``terraform plan`` command.

        https://www.terraform.io/docs/commands/plan.html

        """
        run_module_command(
            self.gen_command("plan", self.env_file + self.options.args["plan"]),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )

    def terraform_workspace_list(self):
        """Execute ``terraform workspace list`` command.

        https://www.terraform.io/docs/commands/workspace/list.html

        Returns:
            str: The available Terraform workspaces.

        """
        self.logger.debug("listing available Terraform workspaces")
        workspaces = subprocess.check_output(
            self.gen_command(["workspace", "list"]), env=self.context.env.vars
        ).decode()
        self.logger.debug("available Terraform workspaces:\n%s", workspaces)
        return workspaces

    def terraform_workspace_new(self, workspace):
        """Execute ``terraform workspace new`` command.

        https://www.terraform.io/docs/commands/workspace/new.html

        Args:
            workspace (str): Terraform workspace to create.

        """
        self.logger.debug("creating workspace: %s", workspace)
        run_module_command(
            self.gen_command(["workspace", "new"], [workspace]),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )
        self.logger.debug("workspace created")

    def terraform_workspace_select(self, workspace):
        """Execute ``terraform workspace select`` command.

        https://www.terraform.io/docs/commands/workspace/select.html

        Args:
            workspace (str): Terraform workspace to select.

        """
        self.logger.debug(
            'switching Terraform workspace from "%s" to "%s"',
            self.current_workspace,
            workspace,
        )
        run_module_command(
            self.gen_command(["workspace", "select"], [workspace]),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )
        del self.current_workspace

    def terraform_workspace_show(self):
        """Execute ``terraform workspace show`` command.

        https://www.terraform.io/docs/commands/workspace/show.html

        Returns:
            str: The current Terraform workspace.

        """
        self.logger.debug("using Terraform to get the current workspace")
        workspace = (
            subprocess.check_output(
                self.gen_command(["workspace", "show"]), env=self.context.env.vars
            )
            .strip()
            .decode()
        )
        self.logger.debug("current Terraform workspace: %s", workspace)
        return workspace

    def run(self, action):
        """Run module."""
        try:
            self.handle_backend()
            if self.skip:
                return
            self.cleanup_dot_terraform()
            self.handle_parameters()
            self.logger.info("init (in progress)")
            self.terraform_init()
            if self.current_workspace != self.required_workspace:
                if re.compile("^[*\\s]\\s%s$" % self.required_workspace, re.M).search(
                    self.terraform_workspace_list()
                ):
                    self.terraform_workspace_select(self.required_workspace)
                else:
                    self.terraform_workspace_new(self.required_workspace)
                self.logger.verbose("re-running init after workspace change...")
                self.terraform_init()
            self.logger.info("init (complete)")
            self.terraform_get()
            self.logger.info("%s (in progress)", action)
            self["terraform_" + action]()
            self.logger.info("%s (complete)", action)
        finally:
            if self.auto_tfvars.exists():
                self.auto_tfvars.unlink()

    def plan(self):
        """Run Terraform plan."""
        self.run("plan")

    def deploy(self):
        """Run Terraform apply."""
        self.run("apply")

    def destroy(self):
        """Run Terraform destroy."""
        self.run("destroy")


class TerraformOptions(ModuleOptions):
    """Module options for Terraform."""

    def __init__(self, args, backend, workspace, version=None, write_auto_tfvars=False):
        """Instantiate class.

        Args:
            args (Union[Dict[str, List[str]], List[str]]): Arguments to append
                to Terraform CLI commands. If providing a list, all arguments
                will be passed to ``terraform apply`` only. Can also be
                provided as a mapping to pass arguments to ``terraform apply``,
                ``terraform init``, and/or ``terraform plan``.
            backend (TerraformBackendConfig): Backend configuration.
            workspace (str): Name of the Terraform workspace to use.
                While it is recommended to let Runway manage this automatically,
                it has been exposed as an option for cases when a static
                workspace needs to be used (e.g. remote backend).
            version (Optional[str]): Terraform version.
            write_auto_tfvars (bool): Optionally write parameters to a tfvars file
                instead of updating environment variables.

        """
        super(TerraformOptions, self).__init__()
        self.args = self._parse_args(args)
        self.backend_config = backend
        self.write_auto_tfvars = write_auto_tfvars
        self.version = version
        self.workspace = workspace

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
        result = {"apply": [], "init": [], "plan": []}

        if isinstance(args, list):
            result["apply"] = args
            return result

        for key in result:
            result[key] = args.get(key, [])

        return result

    @staticmethod
    def resolve_version(context, terraform_version=None, **_):
        """Resolve terraform_version option."""
        if not terraform_version or isinstance(terraform_version, six.string_types):
            return terraform_version
        if isinstance(terraform_version, dict):
            return terraform_version.get(context.env.name, terraform_version.get("*"))
        raise TypeError(
            "terraform_version must be of type str or "
            "Dict[str, str]; got type %s" % type(terraform_version)
        )

    @classmethod
    def parse(cls, context, path=None, **kwargs):  # pylint: disable=arguments-differ
        """Parse the options definition and return an options object.

        Args:
            context (Context): Runway context object.
            path (Optional[Path]): Path to the module.

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
            terraform_workspace (str): Name of the Terraform workspace to use.
                While it is recommended to let Runway manage this automatically,
                it has been exposed as an option for cases when a static
                workspace may be needed.
            terraform_write_auto_tfvars (bool): Optionally write parameters
                to a tfvars file instead of updating environment variables.

        Returns:
            TerraformOptions

        """
        return cls(
            args=kwargs.get("args", []),
            backend=TerraformBackendConfig.parse(context, path, **kwargs),
            version=cls.resolve_version(context, **kwargs),
            workspace=kwargs.get("terraform_workspace", context.env.name),
            write_auto_tfvars=kwargs.get("terraform_write_auto_tfvars", False),
        )


class TerraformBackendConfig(ModuleOptions):
    """Terraform backend configuration module options.

    Attributes:
        OPTIONS (List[str]): A list of option names that are parsed by this
            class.

    """

    OPTIONS = [
        "terraform_backend_config",
        "terraform_backend_cfn_outputs",
        "terraform_backend_ssm_params",
    ]

    def __init__(self, context, config_file=None, **kwargs):
        """Instantiate class.

        See Terraform documentation for the keyword arguments needed for the
        desired backend.

        https://www.terraform.io/docs/backends/types/index.html

        """
        super(TerraformBackendConfig, self).__init__()
        self.__ctx = context
        self._raw_config = kwargs
        self.config_file = config_file

    @cached_property
    def init_args(self):
        """Return command line arguments for init."""
        result = []
        for k, v in self._raw_config.items():
            result.extend(["-backend-config", "{}={}".format(k, v)])
        if not result:
            if self.config_file:
                LOGGER.verbose("using backend config file: %s", self.config_file.name)
                return ["-backend-config=" + self.config_file.name]
            LOGGER.info(
                "backend file not found -- looking for one " "of: %s",
                ", ".join(
                    self.gen_backend_filenames(
                        self.__ctx.env.name, self.__ctx.env.aws_region
                    )
                ),
            )
            return []
        LOGGER.info("using backend values from runway.yml")
        LOGGER.debug("provided backend values: %s", json.dumps(result))
        return result

    def get_full_configuration(self):
        """Get full backend configuration."""
        if not self.config_file:
            return self._raw_config
        result = hcl.loads(self.config_file.read_text())
        result.update(self._raw_config)
        return result

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
        LOGGER.warning(
            "terraform_backend_cfn_outputs option has been deprecated; "
            "use terraform_backend_config with a cfn Lookup"
        )
        if not kwargs:
            return {}

        result = {}
        for key, val in kwargs.items():
            query = deconstruct(val)
            result[key] = find_cfn_output(
                query.output_name,
                client.describe_stacks(StackName=query.stack_name)["Stacks"][0][
                    "Outputs"
                ],
            )
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
        LOGGER.warning(
            "terraform_backend_ssm_params option has been deprecated; "
            "use terraform_backend_config with an ssm Lookup"
        )
        return {
            key: client.get_parameter(Name=val, WithDecryption=True)["Parameter"][
                "Value"
            ]
            for key, val in kwargs.items()
        }

    @staticmethod
    def gen_backend_filenames(environment, region):
        """Generate possible Terraform backend filenames.

        Args:
            environment (str): Current deploy environment.
            region (str): Current AWS region.

        Returns:
            List[str]: List of possible file names.

        """
        formats = [
            "backend-{environment}-{region}.{extension}",
            "backend-{environment}.{extension}",
            "backend-{region}.{extension}",
            "backend.{extension}",
        ]
        result = []
        for fmt in formats:
            for ext in ["hcl", "tfvars"]:
                result.append(
                    fmt.format(environment=environment, extension=ext, region=region)
                )
        return result

    @classmethod
    def get_backend_file(cls, path, environment, region):
        """Determine Terraform backend file.

        Args:
            path (Path): Path to the module.
            environment (str): Current deploy environment.
            region (str): Current AWS region.

        Returns:
            Optional[Path]: Path to a hcl/tfvars file.

        """
        backend_filenames = cls.gen_backend_filenames(environment, region)
        for name in backend_filenames:
            test_path = path / name
            if test_path.is_file():
                return test_path
        return None

    @classmethod
    def parse(cls, context, path=None, **kwargs):  # pylint: disable=arguments-differ
        """Parse backend options and return an options object.

        Args:
            context (Context): Runway context object.
            path (Optional[Path]): Path to the module.

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
        kwargs = cls.merge_nested_env_dicts(
            {key: val for key, val in kwargs.items() if key in cls.OPTIONS},
            context.env.name,
        )
        result = kwargs.get("terraform_backend_config", {})

        session = context.get_session(
            region=result.get("region", context.env.aws_region)
        )

        if kwargs.get("terraform_backend_cfn_outputs"):
            result.update(
                cls.resolve_cfn_outputs(
                    client=session.client("cloudformation"),
                    **kwargs["terraform_backend_cfn_outputs"]
                )
            )
        if kwargs.get("terraform_backend_ssm_params"):
            result.update(
                cls.resolve_ssm_params(
                    client=session.client("ssm"),
                    **kwargs["terraform_backend_ssm_params"]
                )
            )

        if result.get("dynamodb_table") and not result.get("region"):
            # dynamodb_table is the only option exclusive to the s3 backend
            # that can be used to determine if region should be inserted
            result["region"] = context.env.aws_region

        if path:
            result["config_file"] = cls.get_backend_file(
                path, context.env.name, context.env.aws_region
            )
        return cls(context=context, **result)
