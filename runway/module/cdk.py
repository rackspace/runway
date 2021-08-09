"""CDK module."""
from __future__ import annotations

import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from typing_extensions import Literal

from .._logging import PrefixAdaptor
from ..compat import cached_property
from ..config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel
from ..utils import fix_windows_command_list
from .base import ModuleOptions, RunwayModuleNpm
from .utils import generate_node_command, run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))

CdkCommandTypeDef = Literal[
    "bootstrap",
    "context",
    "deploy",
    "destroy",
    "diff",
    "docs",
    "doctor",
    "init",
    "list",
    "metadata",
    "synthesize",
]


class CloudDevelopmentKit(RunwayModuleNpm):
    """CDK Runway Module."""

    options: CloudDevelopmentKitOptions

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
            options=CloudDevelopmentKitOptions.parse_obj(options or {}),
            parameters=parameters,
        )
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    @cached_property
    def cli_args(self) -> List[str]:
        """Generate CLI args from self used in all CDK commands."""
        result: List[str] = []
        if self.ctx.no_color:
            result.append("--no-color")
        if self.ctx.env.debug:
            result.append("--debug")
        elif self.ctx.env.verbose:
            result.append("--verbose")
        return result

    @cached_property
    def cli_args_context(self) -> List[str]:
        """Generate CLI args from self passed to CDK commands as ``--context``."""
        result: List[str] = []
        args = {"environment": self.ctx.env.name}
        args.update(self.parameters)
        for key, val in args.items():
            result.extend(["--context", f"{key}={val}"])
        return result

    @cached_property
    def skip(self) -> bool:
        """Determine if the module should be skipped."""
        if self.package_json_missing():
            self.logger.info(
                'skipped; package.json with "aws-cdk" in dependencies or '
                "devDependencies is required for this module type"
            )
            return True
        if not self.explicitly_enabled:
            self.logger.info("skipped; environment required but not defined")
            return True
        return False

    def cdk_bootstrap(self) -> None:
        """Execute ``cdk bootstrap`` command."""
        self.logger.info("init (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("bootstrap", include_context=True),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("init (complete)")

    def cdk_deploy(self) -> None:
        """Execute ``cdk deploy`` command."""
        self.logger.info("deploy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("deploy", ['"*"'], include_context=True),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("deploy (complete)")

    def cdk_destroy(self) -> None:
        """Execute ``cdk destroy`` command."""
        self.logger.info("destroy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("destroy", ['"*"'], include_context=True),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("destroy (complete)")

    def cdk_diff(self, stack_name: Optional[str] = None) -> None:
        """Execute ``cdk diff`` command."""
        self.logger.info("plan (in progress)")
        try:
            run_module_command(
                cmd_list=self.gen_cmd(
                    "diff",
                    args_list=[stack_name] if stack_name else None,
                    include_context=True,
                ),
                env_vars=self.ctx.env.vars,
                exit_on_error=False,
                logger=self.logger,
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error("CDK returned %s when running diff", exc.returncode)
            self.logger.error(
                "this can be the result of a runtime error or the stack (%s) "
                "differing from what has been deployed if aws-cdk:enableDiffNoFail "
                "is not enabled",
                stack_name,
            )
            # TODO raise error instead of sys.exit() when refactoring cli error handling
            sys.exit(exc.returncode)
        self.logger.info("plan (complete)")

    def cdk_list(self) -> List[str]:
        """Execute ``cdk list`` command."""
        result = subprocess.check_output(
            self.gen_cmd("list", include_context=True),
            env=self.ctx.env.vars,
        ).decode()
        result = result.strip().split("\n")
        LOGGER.debug("found stacks: %s", result)
        return result

    def deploy(self) -> None:
        """Run cdk deploy."""
        if self.skip:
            return
        self.npm_install()
        self.run_build_steps()
        self.cdk_bootstrap()
        self.cdk_deploy()

    def destroy(self) -> None:
        """Run cdk destroy."""
        if self.skip:
            return
        self.npm_install()
        self.run_build_steps()
        self.cdk_destroy()

    def gen_cmd(
        self,
        command: CdkCommandTypeDef,
        args_list: Optional[List[str]] = None,
        *,
        include_context: bool = False,
    ) -> List[str]:
        """Generate and log a CDK command.

        This does not execute the command, only prepares it for use.

        Args:
            command: The CDK command to be executed.
            args_list: Additional arguments to include in the generated command.
            include_context: Optionally, pass context to the CLI. Context is not
                valid for all commands.

        Returns:
            The full command to be passed into a subprocess.

        """
        args = [command] + self.cli_args
        args.extend(args_list or [])
        if include_context:
            args.extend(self.cli_args_context)
        if self.ctx.env.ci:  # append options that remove interaction
            if command == "deploy":
                args.extend(["--ci", "--require-approval=never"])
            if command == "destroy":
                args.append("--force")
        return generate_node_command(
            command="cdk",
            command_opts=args,
            logger=self.logger,
            package="aws-cdk",
            path=self.path,
        )

    def init(self) -> None:
        """Run cdk bootstrap."""
        if self.skip:
            return
        self.npm_install()
        self.run_build_steps()
        self.cdk_bootstrap()

    def plan(self) -> None:
        """Run cdk diff."""
        if self.skip:
            return
        self.npm_install()
        self.run_build_steps()
        for stack_name in self.cdk_list():
            self.cdk_diff(stack_name)

    def run_build_steps(self) -> None:
        """Run build steps."""
        if not self.options.build_steps:
            return
        self.logger.info("build steps (in progress)")
        for step in self.options.build_steps:
            cmd_list = step.split(" ")
            if platform.system() == "Windows":
                cmd_list = fix_windows_command_list(cmd_list)
            try:
                subprocess.check_call(cmd_list, env=self.ctx.env.vars, cwd=self.path)
            except FileNotFoundError:
                self.logger.error(
                    'attempted to run "%s" but failed to find it (are you sure it '
                    "is installed and available in your PATH?)"
                )
                raise
        self.logger.info("build steps (complete)")


class CloudDevelopmentKitOptions(ModuleOptions):
    """Module options for AWS Cloud Development Kit.

    Attributes:
        build_steps: A list of commands to be executed before each action (e.g.
            diff, deploy, destroy).
        data: Options parsed into a data model.
        skip_npm_ci: Skip running ``npm ci`` in the module directory prior to
            processing the module.

    """

    def __init__(self, data: RunwayCdkModuleOptionsDataModel) -> None:
        """Instantiate class.

        Args:
            data: Options parsed into a data model.

        """
        self.build_steps = data.build_steps
        self.data = data
        self.skip_npm_ci = data.skip_npm_ci

    @classmethod
    def parse_obj(cls, obj: object) -> CloudDevelopmentKitOptions:
        """Parse options definition and return an options object.

        Args:
            obj: Object to parse.

        """
        return cls(data=RunwayCdkModuleOptionsDataModel.parse_obj(obj))
