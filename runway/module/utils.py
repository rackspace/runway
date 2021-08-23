"""Runway module utilities."""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from ..utils import which

if TYPE_CHECKING:
    from .._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))
NPM_BIN = "npm.cmd" if platform.system().lower() == "windows" else "npm"
NPX_BIN = "npx.cmd" if platform.system().lower() == "windows" else "npx"


def format_npm_command_for_logging(command: List[str]) -> str:
    """Convert npm command list to string for display to user."""
    if platform.system().lower() == "windows" and (
        command[0] == "npx.cmd" and command[1] == "-c"
    ):
        return f'npx.cmd -c "{" ".join(command[2:])}"'
    return " ".join(command)


def generate_node_command(
    command: str,
    command_opts: List[str],
    path: Path,
    *,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
    package: Optional[str] = None,
) -> List[str]:
    """Return node bin command list for subprocess execution.

    Args:
        command: Command to execute from a local ``node_modules/.bin``.
        command_opts: Options to include with the command.
        path: Current working directory. Used to construct a "fall-back" command
            when ``npx`` is not available/included as part of npm.
        logger: A specific logger to use when logging the constructed command.
        package: Name of the npm package containing the binary to execute.
            This is recommended when the name of the binary does not match the
            name of the npm package.

    """
    if which(NPX_BIN):
        # Use npx if available (npm v5.2+)
        cmd_list = [NPX_BIN]
        if package:
            cmd_list.extend(
                [
                    "--package",
                    package,
                    command,
                    *command_opts,
                ]
            )
        else:
            cmd_list.append("-c")
            cmd_list.append(f"{command} {' '.join(command_opts)}".strip())
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
    """Shell out to provisioner command.

    Args:
        cmd_list: Command to run.
        env_vars: Environment variables.
        exit_on_error: If true, ``subprocess.CalledProcessError`` will be caught
            and the resulting exit code will be passed to ``sys.exit()``.
            If false, the error will not be caught within this function.
            logger: Optionally, supply a logger to use.

    """
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
    with open(os.devnull, "w", encoding="utf-8") as fnull:
        if (
            (path / "package-lock.json").is_file()
            or (path / "npm-shrinkwrap.json").is_file()
        ) and subprocess.call(
            [NPM_BIN, "ci", "-h"], stdout=fnull, stderr=subprocess.STDOUT
        ) == 0:
            return True
    return False
