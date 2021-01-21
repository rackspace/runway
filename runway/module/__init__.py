"""Runway module module."""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union, cast

from ..util import which

if TYPE_CHECKING:
    from .._logging import RunwayLogger
    from ..context.runway import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))
NPM_BIN = "npm.cmd" if platform.system().lower() == "windows" else "npm"
NPX_BIN = "npx.cmd" if platform.system().lower() == "windows" else "npx"


def format_npm_command_for_logging(command: List[str]) -> str:
    """Convert npm command list to string for display to user."""
    if platform.system().lower() == "windows" and (
        command[0] == "npx.cmd" and command[1] == "-c"
    ):
        return 'npx.cmd -c "%s"' % " ".join(command[2:])
    return " ".join(command)


def generate_node_command(
    command: str,
    command_opts: List[str],
    path: Path,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> List[str]:
    """Return node bin command list for subprocess execution."""
    if which(NPX_BIN):
        # Use npx if available (npm v5.2+)
        cmd_list = [NPX_BIN, "-c", "%s %s" % (command, " ".join(command_opts))]
    else:
        logger.debug("npx not found; falling back to invoking shell script directly")
        cmd_list = [str(path / "node_modules" / ".bin" / command), *command_opts]
    logger.debug("node command: %s", format_npm_command_for_logging(cmd_list))
    return cmd_list


def run_module_command(
    cmd_list: List[str],
    env_vars: Dict[str, str],
    exit_on_error: bool = True,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> None:
    """Shell out to provisioner command."""
    logger.debug("running command: %s", " ".join(cmd_list))
    if exit_on_error:
        try:
            subprocess.check_call(cmd_list, env=env_vars)
        except subprocess.CalledProcessError as shelloutexc:
            sys.exit(shelloutexc.returncode)
    else:
        subprocess.check_call(cmd_list, env=env_vars)


def use_npm_ci(path: Path) -> bool:
    """Return true if npm ci should be used in lieu of npm install."""
    # https://docs.npmjs.com/cli/ci#description
    with open(os.devnull, "w") as fnull:
        if (
            (
                (path / "package-lock.json").is_file()
                or (path / "npm-shrinkwrap.json").is_file()
            )
            and subprocess.call(
                [NPM_BIN, "ci", "-h"], stdout=fnull, stderr=subprocess.STDOUT
            )
            == 0
        ):
            return True
    return False


def run_npm_install(
    path: Path,
    options: Dict[str, Union[Dict[str, Any], str]],
    context: RunwayContext,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> None:
    """Run npm install/ci."""
    # Use npm ci if available (npm v5.7+)
    cmd = [NPM_BIN, "<place-holder>"]
    if context.no_color:
        cmd.append("--no-color")
    if cast(Dict[str, Any], options.get("options", {})).get("skip_npm_ci"):
        logger.info("skipped npm ci/npm install")
        return
    if context.env.vars.get("CI") and use_npm_ci(path):
        logger.info("running npm ci...")
        cmd[1] = "ci"
    else:
        logger.info("running npm install...")
        cmd[1] = "install"
    subprocess.check_call(cmd)


def warn_on_boto_env_vars(env_vars: Dict[str, str]) -> None:
    """Inform user if boto-specific environment variables are in use."""
    # https://github.com/serverless/serverless/issues/2151#issuecomment-255646512
    if env_vars.get("AWS_DEFAULT_PROFILE") and not env_vars.get("AWS_PROFILE"):
        LOGGER.warning(
            "AWS_DEFAULT_PROFILE environment variable is set "
            "during use of nodejs-based module and AWS_PROFILE is "
            "not set -- you likely want to set AWS_PROFILE instead"
        )
