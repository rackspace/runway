"""AWS SAM module."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .._logging import PrefixAdaptor
from ..compat import cached_property
from ..config.models.runway.options.sam import RunwaySamModuleOptionsDataModel
from ..exceptions import SamNotFound
from ..utils import which
from .base import ModuleOptions, RunwayModule
from .utils import run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def gen_sam_config_files(stage: str, region: str) -> list[str]:
    """Generate possible SAM config files names."""
    names: list[str] = []
    for ext in ["toml"]:
        # Give preference to explicit stage-region files
        names.append(f"samconfig-{stage}-{region}.{ext}")
        # Fallback to stage name only
        names.append(f"samconfig-{stage}.{ext}")
    # Default samconfig.toml
    names.append("samconfig.toml")
    return names


class SamOptions(ModuleOptions):
    """Module options for AWS SAM.

    Attributes:
        data: Options parsed into a data model.
        build_args: Additional arguments to pass to `sam build`.
        deploy_args: Additional arguments to pass to `sam deploy`.
        skip_build: Skip running `sam build` before deploy.

    """

    def __init__(self, data: RunwaySamModuleOptionsDataModel) -> None:
        """Instantiate class.

        Args:
            data: Options parsed into a data model.

        """
        self.data = data
        self.build_args = data.build_args
        self.deploy_args = data.deploy_args
        self.skip_build = data.skip_build

    @classmethod
    def parse_obj(cls, obj: object) -> SamOptions:
        """Parse options definition and return an options object.

        Args:
            obj: Object to parse.

        """
        return cls(data=RunwaySamModuleOptionsDataModel.model_validate(obj))


class Sam(RunwayModule[SamOptions]):
    """AWS SAM Runway Module."""

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: bool | None = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: str | None = None,
        options: dict[str, Any] | ModuleOptions | None = None,
        parameters: dict[str, Any] | None = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config.
            parameters: Values to pass to SAM that will alter the deployment.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=SamOptions.parse_obj(options or {}),
            parameters=parameters,
        )
        self.logger = PrefixAdaptor(self.name, logger)
        self.stage = self.ctx.env.name
        self.check_for_sam(logger=self.logger)  # fail fast

    @property
    def cli_args(self) -> list[str]:
        """Generate CLI args from self used in all SAM commands."""
        result = ["--region", self.region]
        if "DEBUG" in self.ctx.env.vars:
            result.append("--debug")
        return result

    @cached_property
    def config_file(self) -> Path | None:
        """Find the SAM config file for the module."""
        for name in gen_sam_config_files(self.stage, self.region):
            test_path = self.path / name
            if test_path.is_file():
                return test_path
        return None

    @cached_property
    def template_file(self) -> Path | None:
        """Find the SAM template file for the module."""
        for name in ["template.yaml", "template.yml", "sam.yaml", "sam.yml"]:
            test_path = self.path / name
            if test_path.is_file():
                return test_path
        return None

    @property
    def skip(self) -> bool:
        """Determine if the module should be skipped."""
        if not self.template_file:
            self.logger.info(
                "skipped; SAM template file not found -- looking for one of: %s",
                ", ".join(["template.yaml", "template.yml", "sam.yaml", "sam.yml"]),
            )
            return True

        if self.parameters or self.explicitly_enabled or self.config_file:
            return False

        self.logger.info(
            "skipped; config file for this stage/region not found -- looking for one of: %s",
            ", ".join(gen_sam_config_files(self.stage, self.region)),
        )
        return True

    def gen_cmd(self, command: str, args_list: list[str] | None = None) -> list[str]:
        """Generate and log a SAM command.

        Args:
            command: The SAM command to be executed.
            args_list: Additional arguments to include in the generated command.

        Returns:
            The full command to be passed into a subprocess.

        """
        cmd = ["sam", command]

        # Add template file if found
        if self.template_file:
            cmd.extend(["--template-file", str(self.template_file)])

        # Add config file if found
        if self.config_file:
            cmd.extend(["--config-file", str(self.config_file)])

        # Add common CLI args
        cmd.extend(self.cli_args)

        # Add command-specific args
        cmd.extend(args_list or [])

        # Add no-color if needed
        if self.ctx.no_color:
            cmd.append("--no-color")

        return cmd

    def sam_build(self, *, skip_build: bool = False) -> None:
        """Execute `sam build` command.

        Args:
            skip_build: Skip running the build command.

        """
        if skip_build or self.options.skip_build:
            self.logger.info("skipped sam build")
            return

        self.logger.info("build (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("build", self.options.build_args),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("build (complete)")

    def sam_deploy(self, *, skip_build: bool = False) -> None:
        """Execute `sam deploy` command.

        Args:
            skip_build: Skip running build before deploy.

        """
        if not skip_build:
            self.sam_build()

        self.logger.info("deploy (in progress)")

        # Build deploy command with parameters
        deploy_args = self.options.deploy_args.copy()

        # Add parameter overrides if provided
        if self.parameters:
            param_overrides = []
            for key, value in self.parameters.items():
                param_overrides.append(f"{key}={value}")
            if param_overrides:
                deploy_args.extend(["--parameter-overrides"] + param_overrides)

        # Add stack name based on stage if not already provided
        if not any(arg.startswith("--stack-name") for arg in deploy_args):
            stack_name = f"{self.name}-{self.stage}"
            deploy_args.extend(["--stack-name", stack_name])

        run_module_command(
            cmd_list=self.gen_cmd("deploy", deploy_args),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("deploy (complete)")

    def sam_delete(self) -> None:
        """Execute `sam delete` command."""
        self.logger.info("destroy (in progress)")

        # Build delete command
        delete_args = []

        # Add stack name based on stage
        stack_name = f"{self.name}-{self.stage}"
        delete_args.extend(["--stack-name", stack_name])

        # Add no-prompts for non-interactive mode
        if self.ctx.is_noninteractive:
            delete_args.append("--no-prompts")

        run_module_command(
            cmd_list=self.gen_cmd("delete", delete_args),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("destroy (complete)")

    def deploy(self) -> None:
        """Entrypoint for Runway's deploy action."""
        if self.skip:
            return
        self.sam_deploy()

    def destroy(self) -> None:
        """Entrypoint for Runway's destroy action."""
        if self.skip:
            return
        self.sam_delete()

    def init(self) -> None:
        """Run init."""
        self.logger.warning("init not currently supported for %s", self.__class__.__name__)

    def plan(self) -> None:
        """Entrypoint for Runway's plan action."""
        self.logger.info("plan not currently supported for SAM")

    @staticmethod
    def check_for_sam(*, logger: logging.Logger | PrefixAdaptor | RunwayLogger = LOGGER) -> None:
        """Ensure SAM CLI is installed and in the current path.

        Args:
            logger: Optionally provide a custom logger to use.

        Raises:
            SamNotFound: SAM CLI not found.

        """
        if not which("sam"):
            logger.error(
                '"sam" not found in path or is not executable; '
                "please ensure AWS SAM CLI is installed correctly"
            )
            raise SamNotFound
