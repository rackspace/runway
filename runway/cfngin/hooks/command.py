"""Command hook."""
import logging
import os
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Optional, Union

from typing_extensions import TypedDict

from ..exceptions import ImproperlyConfigured

LOGGER = logging.getLogger(__name__)


class RunCommandResponseTypeDef(TypedDict, total=False):
    """Response from run_command."""

    returncode: int
    stderr: str
    stdout: str


def run_command(
    *,
    command: Union[str, List[str]],
    capture: bool = False,
    interactive: bool = False,
    ignore_status: bool = False,
    quiet: bool = False,
    stdin: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> RunCommandResponseTypeDef:
    """Run a custom command as a hook.

    Args:
        command: Command(s) to run.
        capture: If enabled, capture the command's stdout and stderr,
            and return them in the hook result.
        interactive: If enabled, allow the command to interact with
            stdin. Otherwise, stdin will be set to the null device.
        ignore_status: Don't fail the hook if the command returns a
            non-zero status.
        quiet: Redirect the command's stdout and stderr to the null device,
            silencing all output. Should not be enabled if ``capture`` is also
            enabled.
        stdin: String to send to the stdin of the command. Implicitly disables
            ``interactive``.
        env: Dictionary of environment variable overrides for the command context.
            Will be merged with the current environment.

    Additional keyword arguments passed to the function will be forwarded to the
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
    # remove unneeded args from kwargs
    kwargs.pop("context", None)
    kwargs.pop("provider", None)

    if quiet and capture:
        raise ImproperlyConfigured(
            __name__ + ".run_command",
            ValueError("Cannot enable `quiet` and `capture` options simultaneously"),
        )

    with open(os.devnull, "wb") as devnull:
        if quiet:
            out_err_type = devnull
        elif capture:
            out_err_type = PIPE
        else:
            out_err_type = None

        if interactive:
            in_type = None
        elif stdin:
            in_type = PIPE
        else:
            in_type = devnull

        if env:
            full_env = os.environ.copy()
            full_env.update(env)
            env = full_env

        LOGGER.info("running command: %s", command)

        with Popen(
            command,
            stdin=in_type,
            stdout=out_err_type,
            stderr=out_err_type,
            env=env,
            **kwargs,
        ) as proc:
            try:
                out, err = proc.communicate(stdin)
                status = proc.wait()

                if status == 0 or ignore_status:
                    return {"returncode": proc.returncode, "stdout": out, "stderr": err}

                # Don't print the command line again if we already did earlier
                if LOGGER.isEnabledFor(logging.INFO):
                    LOGGER.warning("command failed with returncode %d", status)
                else:
                    LOGGER.warning(
                        "command failed with returncode %d: %s", status, command
                    )

                return {}
            except Exception:  # pylint: disable=broad-except
                return {}
