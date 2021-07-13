"""Terraform module."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

import hcl
from send2trash import send2trash
from typing_extensions import Literal

from .._logging import PrefixAdaptor
from ..compat import cached_property
from ..config.models.runway.options.terraform import (
    RunwayTerraformBackendConfigDataModel,
    RunwayTerraformModuleOptionsDataModel,
)
from ..env_mgr.tfenv import TFEnvManager, VersionTuple
from ..utils import DOC_SITE, which
from .base import ModuleOptions, RunwayModule
from .utils import run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext
    from ..core.components import DeployEnvironment

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def gen_workspace_tfvars_files(environment: str, region: str) -> List[str]:
    """Generate possible Terraform workspace tfvars filenames."""
    return [
        # Give preference to explicit environment-region files
        f"{environment}-{region}.tfvars",
        # Fallback to environment name only
        f"{environment}.tfvars",
    ]


def update_env_vars_with_tf_var_values(
    os_env_vars: Dict[str, str],
    tf_vars: Dict[str, Union[Dict[str, Any], List[Any], str]],
) -> Dict[str, str]:
    """Return os_env_vars with TF_VAR values for each tf_var."""
    # https://www.terraform.io/docs/commands/environment-variables.html#tf_var_name
    for key, val in tf_vars.items():
        if isinstance(val, dict):
            value = ", ".join(
                nestedkey + ' = "' + nestedval + '"'
                for (nestedkey, nestedval) in val.items()
            )
            os_env_vars[f"TF_VAR_{key}"] = f"{{ {value} }}"
        elif isinstance(val, list):
            os_env_vars[f"TF_VAR_{key}"] = json.dumps(val)
        else:
            os_env_vars[f"TF_VAR_{key}"] = val
    return os_env_vars


TerraformActionTypeDef = Literal[
    "apply",
    "destroy",
    "get",
    "init",
    "plan",
    "workspace_list",
    "workspace_new",
    "workspace_select",
    "workspace_show",
]


class Terraform(RunwayModule):
    """Terraform Runway Module."""

    options: TerraformOptions

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=TerraformOptions.parse_obj(
                deploy_environment=context.env, obj=options or {}, path=module_root
            ),
            parameters=parameters,
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, logger)
        self.required_workspace = self.options.workspace

    @cached_property
    def auto_tfvars(self) -> Path:
        """Return auto.tfvars file if one is being used."""
        file_path = self.path / "runway-parameters.auto.tfvars.json"
        if self.parameters and self.options.write_auto_tfvars:
            if self.version < (0, 10):
                self.logger.warning(
                    "Terraform version does not support the use of "
                    "*.auto.tfvars; some variables may be missing"
                )
            file_path.write_text(json.dumps(self.parameters, indent=4))
        return file_path

    @cached_property
    def current_workspace(self) -> str:
        """Wrap "terraform_workspace_show" to cache the value.

        Returns:
            The currently active Terraform workspace.

        """
        return self.terraform_workspace_show()

    @cached_property
    def env_file(self) -> List[str]:
        """Find the environment file for the module."""
        result: List[str] = []
        for name in gen_workspace_tfvars_files(
            self.ctx.env.name, self.ctx.env.aws_region
        ):
            test_path = self.path / name
            if test_path.is_file():
                result.append("-var-file=" + test_path.name)
                break  # stop looking if one is found
        return result

    @property
    def skip(self) -> bool:
        """Determine if the module should be skipped."""
        if self.parameters or self.env_file:
            return False
        self.logger.info(
            "skipped; tfvars file for this environmet/region not found "
            "and no parameters provided -- looking for one of: %s",
            ", ".join(
                gen_workspace_tfvars_files(self.ctx.env.name, self.ctx.env.aws_region)
            ),
        )
        return True

    @cached_property
    def tfenv(self) -> TFEnvManager:
        """Terraform environmet manager."""
        return TFEnvManager(self.path)

    @cached_property
    def tf_bin(self) -> str:
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

    @cached_property
    def version(self) -> VersionTuple:
        """Version of Terraform being used."""
        if not self.tfenv.current_version and self.options.version:
            self.tfenv.set_version(self.options.version)
        if self.tfenv.version:
            return self.tfenv.version
        version = self.tfenv.get_version_from_executable(self.tf_bin)
        if version:
            return version
        raise ValueError(f"unable to retrieve version from {self.tf_bin}")

    def cleanup_dot_terraform(self) -> None:
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
            send2trash(str(child))  # does not support Path objects

    def deploy(self) -> None:
        """Run Terraform apply."""
        self.run("apply")

    def destroy(self) -> None:
        """Run Terraform destroy."""
        self.run("destroy")

    def gen_command(
        self,
        command: Union[List[str], str, Tuple[str, ...]],
        args_list: Optional[List[str]] = None,
    ) -> List[str]:
        """Generate Terraform command."""
        if isinstance(command, (list, tuple)):
            cmd = [self.tf_bin, *command]
        else:
            cmd = [self.tf_bin, command]
        cmd.extend(args_list or [])
        if self.ctx.no_color:
            cmd.append("-no-color")
        return cmd

    def handle_backend(self) -> None:
        """Handle backend configuration.

        This needs to be run before "skip" is assessed or env_file/auto_tfvars
        is used in case their behavior needs to be altered.

        """
        if not self.tfenv.backend["type"]:
            self.logger.info(
                "unable to determine backend for module; no special handling "
                "will be applied"
            )
            return
        handler = f"_{self.tfenv.backend['type']}_backend_handler"
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
            self[f"_{self.tfenv.backend['type']}_backend_handler"]()
        else:
            self.logger.verbose(
                'backed "%s" does not require special handling',
                self.tfenv.backend["type"],
                exc_info=True,
            )

    def _remote_backend_handler(self) -> None:
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
            self.ctx.env.vars.update({"TF_WORKSPACE": self.ctx.env.name})
            self.logger.verbose(
                'set environment variable "TF_WORKSPACE" to avoid prompt '
                "during init by pre-selecting an appropriate workspace"
            )

        if self.tfenv.backend["config"]["workspaces"].get("name"):
            self.logger.verbose(
                "handling use of backend config: remote.workspaces.name"
            )
            # this can't be set or it will cause errors
            self.ctx.env.vars.pop("TF_WORKSPACE", None)
            self.required_workspace = "default"
            self.logger.info(
                'forcing use of static workspace "default"; '
                'required for use of "backend.remote.workspaces.name"'
            )

    def handle_parameters(self) -> None:
        """Handle parameters.

        Either updating environment variables or writing to a file.

        """
        if self.auto_tfvars.exists():
            return

        self.ctx.env.vars = update_env_vars_with_tf_var_values(
            self.ctx.env.vars, self.parameters
        )

    def init(self) -> None:
        """Run init."""
        self.run("init")

    def plan(self) -> None:
        """Run Terraform plan."""
        self.run("plan")

    def terraform_apply(self) -> None:
        """Execute ``terraform apply`` command.

        https://www.terraform.io/docs/cli/commands/apply.html

        """
        args_list = self.env_file + self.options.args.apply
        if self.ctx.env.ci:
            args_list.append("-auto-approve=true")
        else:
            args_list.append("-auto-approve=false")
        run_module_command(
            self.gen_command("apply", args_list),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def terraform_destroy(self) -> None:
        """Execute ``terraform destroy`` command.

        https://www.terraform.io/docs/cli/commands/destroy.html

        """
        if self.version >= (0, 15, 2):
            return self._terraform_destroy_15_2()
        if self.version >= (0, 12):
            return self._terraform_destroy_12()
        return self._terraform_destroy_legacy()

    def _terraform_destroy_12(self) -> None:
        """Execute ``terraform destroy -auto-approve`` command.

        Compatible with Terraform >=0.12.0, <0.15.2.

        """
        return run_module_command(
            self.gen_command("destroy", ["-auto-approve"] + self.env_file),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def _terraform_destroy_15_2(self) -> None:
        """Execute ``terraform apply -destroy -auto-approve`` command.

        Compatible with Terraform >=0.15.2.

        """
        return run_module_command(
            self.gen_command("apply", ["-destroy", "-auto-approve"] + self.env_file),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def _terraform_destroy_legacy(self) -> None:
        """Execute ``terraform destroy -force`` command.

        Compatible with Terrafrom <0.12.0.

        """
        return run_module_command(
            self.gen_command("destroy", ["-force"] + self.env_file),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def terraform_get(self) -> None:
        """Execute ``terraform get`` command.

        https://www.terraform.io/docs/cli/commands/get.html

        """
        self.logger.info("downloading and updating Terraform modules")
        run_module_command(
            self.gen_command("get", ["-update=true"]),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def terraform_init(self) -> None:
        """Execute ``terraform init`` command.

        https://www.terraform.io/docs/cli/commands/init.html

        """
        cmd = self.gen_command(
            "init",
            ["-reconfigure"]
            + self.options.backend_config.init_args
            + self.options.args.init,
        )
        try:
            run_module_command(
                cmd,
                env_vars=self.ctx.env.vars,
                exit_on_error=False,
                logger=self.logger,
            )
        except subprocess.CalledProcessError as shelloutexc:
            # cleaner output by not letting the exception raise
            sys.exit(shelloutexc.returncode)

    def terraform_plan(self) -> None:
        """Execute ``terraform plan`` command.

        https://www.terraform.io/docs/cli/commands/plan.html

        """
        run_module_command(
            self.gen_command("plan", self.env_file + self.options.args.plan),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )

    def terraform_workspace_list(self) -> str:
        """Execute ``terraform workspace list`` command.

        https://www.terraform.io/docs/cli/commands/workspace/list.html

        Returns:
            str: The available Terraform workspaces.

        """
        self.logger.debug("listing available Terraform workspaces")
        workspaces = subprocess.check_output(
            self.gen_command(["workspace", "list"]), env=self.ctx.env.vars
        ).decode()
        self.logger.debug("available Terraform workspaces:\n%s", workspaces)
        return workspaces

    def terraform_workspace_new(self, workspace: str) -> None:
        """Execute ``terraform workspace new`` command.

        permanently to https://www.terraform.io/docs/cli/commands/workspace/new.html

        Args:
            workspace: Terraform workspace to create.

        """
        self.logger.debug("creating workspace: %s", workspace)
        run_module_command(
            self.gen_command(["workspace", "new"], [workspace]),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.debug("workspace created")

    def terraform_workspace_select(self, workspace: str) -> None:
        """Execute ``terraform workspace select`` command.

        https://www.terraform.io/docs/cli/commands/workspace/select.html

        Args:
            workspace: Terraform workspace to select.

        """
        self.logger.debug(
            'switching Terraform workspace from "%s" to "%s"',
            self.current_workspace,
            workspace,
        )
        run_module_command(
            self.gen_command(["workspace", "select"], [workspace]),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        del self.current_workspace

    def terraform_workspace_show(self) -> str:
        """Execute ``terraform workspace show`` command.

        https://www.terraform.io/docs/cli/commands/workspace/show.html

        Returns:
            The current Terraform workspace.

        """
        self.logger.debug("using Terraform to get the current workspace")
        workspace = (
            subprocess.check_output(
                self.gen_command(["workspace", "show"]), env=self.ctx.env.vars
            )
            .strip()
            .decode()
        )
        self.logger.debug("current Terraform workspace: %s", workspace)
        return workspace

    def run(self, action: TerraformActionTypeDef) -> None:
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
                if re.compile(f"^[*\\s]\\s{self.required_workspace}$", re.M).search(
                    self.terraform_workspace_list()
                ):
                    self.terraform_workspace_select(self.required_workspace)
                else:
                    self.terraform_workspace_new(self.required_workspace)
                self.logger.verbose("re-running init after workspace change...")
                self.terraform_init()
            self.terraform_get()
            self.logger.info("init (complete)")
            if action != "init":
                self.logger.info("%s (in progress)", action)
                self["terraform_" + action]()
                self.logger.info("%s (complete)", action)
        finally:
            if self.auto_tfvars.exists():
                self.auto_tfvars.unlink()


class TerraformOptions(ModuleOptions):
    """Module options for Terraform.

    Attributes:
        args: CLI arguments/options to pass to Terraform.
        data: Options parsed into a data model.
        env: Current deploy environment.
        path: Module path.
        version: String continaing a Terraform version.
        write_auto_tfvars: Optionally write parameters to a tfvars file instead
            of updating variables.

    """

    def __init__(
        self,
        data: RunwayTerraformModuleOptionsDataModel,
        deploy_environment: DeployEnvironment,
        path: Optional[Path] = None,
    ) -> None:
        """Instantiate class.

        Args:
            deploy_environment: Current deploy environment.
            data: Options parsed into a data model.
            path: Module path.

        """
        self.args = data.args
        self.data = data
        self.env = deploy_environment
        self.path = path or Path.cwd()
        self.version = data.version
        self.workspace = data.workspace or deploy_environment.name
        self.write_auto_tfvars = data.write_auto_tfvars

    @cached_property
    def backend_config(self) -> TerraformBackendConfig:
        """Backend configuration options."""
        return TerraformBackendConfig.parse_obj(
            deploy_environment=self.env,
            obj=self.data.backend_config or {},
            path=self.path,
        )

    @classmethod
    def parse_obj(
        cls,
        deploy_environment: DeployEnvironment,
        obj: object,
        path: Optional[Path] = None,
    ) -> TerraformOptions:
        """Parse options definition and return an options object.

        Args:
            deploy_environment: Current deploy environment.
            obj: Object to parse.
            path: Module path.

        """
        return cls(
            data=RunwayTerraformModuleOptionsDataModel.parse_obj(obj),
            deploy_environment=deploy_environment,
            path=path or Path.cwd(),
        )


class TerraformBackendConfig(ModuleOptions):
    """Terraform backend configuration module options."""

    def __init__(
        self,
        data: RunwayTerraformBackendConfigDataModel,
        deploy_environment: DeployEnvironment,
        path: Path,
    ) -> None:
        """Instantiate class.

        Args:
            data: Options parsed into a data model.
            deploy_environment: Current deploy environment.
            path: Module path.

        """
        self.bucket = data.bucket
        self.data = data
        self.dynamodb_table = data.dynamodb_table
        self.env = deploy_environment
        self.path = path
        if data and not data.region:
            data.region = deploy_environment.aws_region  # default to region from env
        self.region = data.region

    @cached_property
    def config_file(self) -> Optional[Path]:
        """Backend configuration file."""
        return self.get_backend_file(self.path, self.env.name, self.env.aws_region)

    @cached_property
    def init_args(self) -> List[str]:
        """Return command line arguments for init."""
        result: List[str] = []
        for k, v in self.data.dict(exclude_none=True).items():
            result.extend(["-backend-config", f"{k}={v}"])
        if not result:
            if self.config_file:
                LOGGER.verbose("using backend config file: %s", self.config_file.name)
                return [f"-backend-config={self.config_file.name}"]
            LOGGER.info(
                "backend file not found -- looking for one " "of: %s",
                ", ".join(
                    self.gen_backend_filenames(self.env.name, self.env.aws_region)
                ),
            )
            return []
        LOGGER.info("using backend values from runway.yml")
        LOGGER.debug("provided backend values: %s", json.dumps(result))
        return result

    def get_full_configuration(self) -> Dict[str, str]:
        """Get full backend configuration."""
        if not self.config_file:
            return self.data.dict(exclude_none=True)
        result = cast(Dict[str, str], hcl.loads(self.config_file.read_text()))
        result.update(self.data.dict(exclude_none=True))
        return result

    @classmethod
    def get_backend_file(
        cls, path: Path, environment: str, region: str
    ) -> Optional[Path]:
        """Determine Terraform backend file.

        Args:
            path: Path to the module.
            environment: Current deploy environment.
            region: Current AWS region.

        """
        backend_filenames = cls.gen_backend_filenames(environment, region)
        for name in backend_filenames:
            test_path = path / name
            if test_path.is_file():
                return test_path
        return None

    @staticmethod
    def gen_backend_filenames(environment: str, region: str) -> List[str]:
        """Generate possible Terraform backend filenames.

        Args:
            environment: Current deploy environment.
            region : Current AWS region.

        """
        formats = [
            "backend-{environment}-{region}.{extension}",
            "backend-{environment}.{extension}",
            "backend-{region}.{extension}",
            "backend.{extension}",
        ]
        result: List[str] = []
        for fmt in formats:
            for ext in ["hcl", "tfvars"]:
                result.append(
                    fmt.format(environment=environment, extension=ext, region=region)
                )
        return result

    @classmethod
    def parse_obj(
        cls,
        deploy_environment: DeployEnvironment,
        obj: object,
        path: Optional[Path] = None,
    ) -> TerraformBackendConfig:
        """Parse options definition and return an options object.

        Args:
            deploy_environment: Current deploy environment.
            obj: Object to parse.
            path: Module path.

        """
        return cls(
            data=RunwayTerraformBackendConfigDataModel.parse_obj(obj),
            deploy_environment=deploy_environment,
            path=path or Path.cwd(),
        )
