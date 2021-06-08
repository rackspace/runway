"""CDK module."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from .._logging import PrefixAdaptor
from ..config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel
from ..utils import change_dir, run_commands, which
from .base import ModuleOptions, RunwayModuleNpm
from .utils import generate_node_command, run_module_command

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def get_cdk_stacks(
    module_path: Path, env_vars: Dict[str, str], context_opts: List[str]
) -> List[str]:
    """Return list of CDK stacks."""
    LOGGER.debug("listing stacks in the CDK app prior to diff...")
    result = subprocess.check_output(
        generate_node_command(
            command="cdk",
            command_opts=["list"] + context_opts,
            package="aws-cdk",
            path=module_path,
        ),
        env=env_vars,
    ).decode()
    result = result.strip().split("\n")
    LOGGER.debug("found stacks: %s", result)
    return result


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

    def run_cdk(  # pylint: disable=too-many-branches
        self, command: str = "deploy"
    ) -> Dict[str, bool]:
        """Run CDK."""
        response = {"skipped_configs": False}
        cdk_opts = [command]
        if self.ctx.no_color:
            cdk_opts.append("--no-color")

        if not which("npm"):
            self.logger.error(
                '"npm" not found in path or is not executable; '
                "please ensure it is installed correctly."
            )
            sys.exit(1)

        if "DEBUG" in self.ctx.env.vars:
            cdk_opts.append("-v")  # Increase logging if requested

        if self.explicitly_enabled:
            if not self.package_json_missing():
                with change_dir(self.path):
                    self.npm_install()
                    if self.options.build_steps:
                        self.logger.info("build steps (in progress)")
                        run_commands(
                            commands=cast(
                                List[
                                    Union[
                                        str, List[str], Dict[str, Union[str, List[str]]]
                                    ]
                                ],
                                self.options.build_steps,
                            ),
                            directory=self.path,
                            env=self.ctx.env.vars,
                        )
                        self.logger.info("build steps (complete)")
                    cdk_context_opts: List[str] = []
                    for key, val in cast(Dict[str, str], self.parameters).items():
                        cdk_context_opts.extend(["--context", "%s=%s" % (key, val)])
                    cdk_opts.extend(cdk_context_opts)
                    if command == "diff":
                        self.logger.info("plan (in progress)")
                        for i in get_cdk_stacks(
                            self.path, self.ctx.env.vars, cdk_context_opts
                        ):
                            subprocess.call(
                                generate_node_command(  # 'diff <stack>'
                                    command="cdk",
                                    command_opts=cdk_opts + [i],
                                    package="aws-cdk",
                                    path=self.path,
                                ),
                                env=self.ctx.env.vars,
                            )
                        self.logger.info("plan (complete)")
                    else:
                        # Make sure we're targeting all stacks
                        if command in ["deploy", "destroy"]:
                            cdk_opts.append('"*"')

                        if command == "deploy":
                            if "CI" in self.ctx.env.vars:
                                cdk_opts.append("--ci")
                                cdk_opts.append("--require-approval=never")
                            bootstrap_command = generate_node_command(
                                command="cdk",
                                command_opts=["bootstrap"]
                                + cdk_context_opts
                                + (["--no-color"] if self.ctx.no_color else []),
                                package="aws-cdk",
                                path=self.path,
                            )
                            self.logger.info("bootstrap (in progress)")
                            run_module_command(
                                cmd_list=bootstrap_command,
                                env_vars=self.ctx.env.vars,
                                logger=self.logger,
                            )
                            self.logger.info("bootstrap (complete)")
                        elif command == "destroy" and self.ctx.is_noninteractive:
                            cdk_opts.append("-f")  # Don't prompt
                        cdk_command = generate_node_command(
                            command="cdk",
                            command_opts=cdk_opts,
                            package="aws-cdk",
                            path=self.path,
                        )
                        self.logger.info("%s (in progress)", command)
                        run_module_command(
                            cmd_list=cdk_command,
                            env_vars=self.ctx.env.vars,
                            logger=self.logger,
                        )
                        self.logger.info("%s (complete)", command)
            else:
                self.logger.info(
                    'skipped; package.json with "aws-cdk" in devDependencies is '
                    "required for this module type"
                )
        else:
            self.logger.info("skipped; environment required but not defined")
            response["skipped_configs"] = True
        return response

    def plan(self) -> None:
        """Run cdk diff."""
        self.run_cdk(command="diff")

    def deploy(self) -> None:
        """Run cdk deploy."""
        self.run_cdk(command="deploy")

    def destroy(self) -> None:
        """Run cdk destroy."""
        self.run_cdk(command="destroy")


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
