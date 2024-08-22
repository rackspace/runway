"""Command hook."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from typing_extensions import TypedDict

from ...utils import BaseModel
from ..exceptions import ImproperlyConfigured

LOGGER = logging.getLogger(__name__)


class RunCommandHookArgs(BaseModel):
    """Hook arguments for ``run_command``."""

    capture: bool = False
    """If enabled, capture the command's stdout and stderr, and return them in the hook result."""

    command: str | list[str]
    """Command(s) to run."""

    env: dict[str, str] | None = None
    """Dictionary of environment variable overrides for the command context.
    Will be merged with the current environment.

    """

    ignore_status: bool = False
    """Don't fail the hook if the command returns a non-zero status."""

    interactive: bool = False
    """If enabled, allow the command to interact with stdin.
    Otherwise, stdin will be set to the null device.

    """

    quiet: bool = False
    """Redirect the command's stdout and stderr to the null device, silencing all output.
    Should not be enabled if ``capture`` is also enabled.

    """

    stdin: str | None = None
    """String to send to the stdin of the command. Implicitly disables ``interactive``."""


class RunCommandResponseTypeDef(TypedDict, total=False):
    """Response from run_command."""

    returncode: int
    stderr: str
    stdout: str


def run_command(*_args: Any, **kwargs: Any) -> RunCommandResponseTypeDef:  # noqa: C901, PLR0912
    """Run a custom command as a hook.

    Arguments not parsed by the data model will be forwarded to the
    ``subprocess.Popen`` function. Interesting ones include: ``cwd`` and ``shell``.

    Examples:
        .. code-block:: yaml

            pre_deploy:
              command_copy_environment:
                path: runway.cfngin.hooks.command.run_command
                required: true
                enabled: true
                data_key: copy_env
                args:
                  command: ['cp', 'environment.template', 'environment']
              command_git_rev_parse:
                path: runway.cfngin.hooks.command.run_command
                required: true
                enabled: true
                data_key: get_git_commit
                args:
                  command: ['git', 'rev-parse', 'HEAD']
                  cwd: ./my-git-repo
                  capture: true
              command_npm_install:
                path: runway.cfngin.hooks.command.run_command
                args:
                  command: '`cd $PROJECT_DIR/project; npm install`'
                  env:
                    PROJECT_DIR: ./my-project
                    shell: true

    """
    args = RunCommandHookArgs.model_validate(kwargs)

    # remove parsed args from kwargs
    for field in RunCommandHookArgs.model_fields:
        kwargs.pop(field, None)

    # remove unneeded args from kwargs
    kwargs.pop("context", None)
    kwargs.pop("provider", None)

    if args.quiet and args.capture:
        raise ImproperlyConfigured(
            __name__ + ".run_command",
            ValueError("Cannot enable `quiet` and `capture` options simultaneously"),
        )

    with open(os.devnull, "wb") as devnull:  # noqa: PTH123
        if args.quiet:
            out_err_type = devnull
        elif args.capture:
            out_err_type = subprocess.PIPE
        else:
            out_err_type = None

        if args.interactive:
            in_type = None
        elif args.stdin:
            in_type = subprocess.PIPE
        else:
            in_type = devnull

        if args.env:
            full_env = os.environ.copy()
            full_env.update(args.env)
            args.env = full_env

        LOGGER.info("running command: %s", args.command)

        with subprocess.Popen(
            args.command,
            stdin=in_type,
            stdout=out_err_type,
            stderr=out_err_type,
            env=args.env,
            **kwargs,
        ) as proc:
            try:
                out, err = proc.communicate(args.stdin)
                status = proc.wait()

                if status == 0 or args.ignore_status:
                    return {"returncode": proc.returncode, "stdout": out, "stderr": err}

                # Don't print the command line again if we already did earlier
                if LOGGER.isEnabledFor(logging.INFO):  # cov: ignore
                    LOGGER.warning("command failed with returncode %d", status)
                else:
                    LOGGER.warning("command failed with returncode %d: %s", status, args.command)

                return {}
            except Exception:  # cov: ignore  # noqa: BLE001
                return {}
