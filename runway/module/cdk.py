"""CDK module."""
import logging
import os
import subprocess
import sys

from .._logging import PrefixAdaptor
from ..util import change_dir, run_commands, which
from . import (
    RunwayModule,
    generate_node_command,
    run_module_command,
    run_npm_install,
    warn_on_boto_env_vars,
)

LOGGER = logging.getLogger(__name__)


def get_cdk_stacks(module_path, env_vars, context_opts):
    """Return list of CDK stacks."""
    LOGGER.debug("listing stacks in the CDK app prior to diff...")
    result = subprocess.check_output(
        generate_node_command(
            command="cdk", command_opts=["list"] + context_opts, path=module_path
        ),
        env=env_vars,
    )
    if isinstance(result, bytes):  # python3 returns encoded bytes
        result = result.decode()
    result = result.strip().split("\n")
    LOGGER.debug("found stacks: %s", result)
    return result


class CloudDevelopmentKit(RunwayModule):
    """CDK Runway Module."""

    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (Union[str, Path]): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        super(CloudDevelopmentKit, self).__init__(context, path, options)
        # logger needs to be created here to use the correct logger
        self.logger = PrefixAdaptor(self.name, LOGGER)

    def run_cdk(self, command="deploy"):  # pylint: disable=too-many-branches
        """Run CDK."""
        response = {"skipped_configs": False}
        cdk_opts = [command]
        if self.context.no_color:
            cdk_opts.append("--no-color")

        if not which("npm"):
            self.logger.error(
                '"npm" not found in path or is not executable; '
                "please ensure it is installed correctly."
            )
            sys.exit(1)

        if "DEBUG" in self.context.env.vars:
            cdk_opts.append("-v")  # Increase logging if requested

        warn_on_boto_env_vars(self.context.env.vars)

        if self.options["environment"]:
            if os.path.isfile(os.path.join(self.path, "package.json")):
                with change_dir(self.path):
                    run_npm_install(
                        self.path, self.options, self.context, logger=self.logger
                    )
                    if self.options.get("options", {}).get("build_steps", []):
                        self.logger.info("build steps (in progress)")
                        run_commands(
                            commands=self.options.get("options", {}).get(
                                "build_steps", []
                            ),
                            directory=self.path,
                            env=self.context.env.vars,
                        )
                        self.logger.info("build steps (complete)")
                    cdk_context_opts = []
                    for (key, val) in self.options["parameters"].items():
                        cdk_context_opts.extend(["-c", "%s=%s" % (key, val)])
                    cdk_opts.extend(cdk_context_opts)
                    if command == "diff":
                        self.logger.info("plan (in progress)")
                        for i in get_cdk_stacks(
                            self.path, self.context.env.vars, cdk_context_opts
                        ):
                            subprocess.call(
                                generate_node_command(
                                    "cdk", cdk_opts + [i], self.path  # 'diff <stack>'
                                ),
                                env=self.context.env.vars,
                            )
                        self.logger.info("plan (complete)")
                    else:
                        # Make sure we're targeting all stacks
                        if command in ["deploy", "destroy"]:
                            cdk_opts.append('"*"')

                        if command == "deploy":
                            if "CI" in self.context.env.vars:
                                cdk_opts.append("--ci")
                                cdk_opts.append("--require-approval=never")
                            bootstrap_command = generate_node_command(
                                "cdk",
                                ["bootstrap"]
                                + cdk_context_opts
                                + (["--no-color"] if self.context.no_color else []),
                                self.path,
                            )
                            self.logger.info("bootstrap (in progress)")
                            run_module_command(
                                cmd_list=bootstrap_command,
                                env_vars=self.context.env.vars,
                                logger=self.logger,
                            )
                            self.logger.info("bootstrap (complete)")
                        elif command == "destroy" and self.context.is_noninteractive:
                            cdk_opts.append("-f")  # Don't prompt
                        cdk_command = generate_node_command("cdk", cdk_opts, self.path)
                        self.logger.info("%s (in progress)", command)
                        run_module_command(
                            cmd_list=cdk_command,
                            env_vars=self.context.env.vars,
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

    def plan(self):
        """Run cdk diff."""
        self.run_cdk(command="diff")

    def deploy(self):
        """Run cdk deploy."""
        self.run_cdk(command="deploy")

    def destroy(self):
        """Run cdk destroy."""
        self.run_cdk(command="destroy")
