"""Command hook."""
# pylint: disable=unused-argument
import logging
import os
from subprocess import PIPE, Popen

from ..exceptions import ImproperlyConfigured

LOGGER = logging.getLogger(__name__)


def _devnull():
    return open(os.devnull, "wb")


def run_command(
    provider,
    context,
    command,
    capture=False,
    interactive=False,
    ignore_status=False,
    quiet=False,
    stdin=None,
    env=None,
    **kwargs
):
    """Run a custom command as a hook.

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance. (passed in by CFNgin)
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        command (Union[str, List[str]]): Command(s) to run.
        capture (bool): If enabled, capture the command's stdout and stderr,
            and return them in the hook result. (*default:* ``False``)
        interactive (bool): If enabled, allow the command to interact with
            stdin. Otherwise, stdin will be set to the null device.
            (*default:* ``False``)
        ignore_status (bool): Don't fail the hook if the command returns a
            non-zero status. (*default:* ``False``)
        quiet (bool): Redirect the command's stdout and stderr to the null
            device, silencing all output. Should not be enabled if
            ``capture`` is also enabled. (*default:* ``False``)
        stdin (Optional[str]): String to send to the stdin of the command.
            Implicitly disables ``interactive``.
        env (Optional[Dict[str, str]]): Dictionary of environment variable
            overrides for the command context. Will be merged with the current
            environment.
        **kwargs (Any): Any other arguments will be forwarded to the
            ``subprocess.Popen`` function. Interesting ones include: ``cwd``
            and ``shell``.

    Examples:
        .. code-block:: yaml

            pre_build:
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
    if quiet and capture:
        raise ImproperlyConfigured(
            __name__ + ".run_command",
            "Cannot enable `quiet` and `capture` options simultaneously",
        )

    if quiet:
        out_err_type = _devnull()
    elif capture:
        out_err_type = PIPE
    else:
        out_err_type = None

    if interactive:
        in_type = None
    elif stdin:
        in_type = PIPE
    else:
        in_type = _devnull()

    if env:
        full_env = os.environ.copy()
        full_env.update(env)
        env = full_env

    LOGGER.info("running command: %s", command)

    proc = Popen(
        command,
        stdin=in_type,
        stdout=out_err_type,
        stderr=out_err_type,
        env=env,
        **kwargs
    )
    try:
        out, err = proc.communicate(stdin)
        status = proc.wait()

        if status == 0 or ignore_status:
            return {"returncode": proc.returncode, "stdout": out, "stderr": err}

        # Don't print the command line again if we already did earlier
        if LOGGER.isEnabledFor(logging.INFO):
            LOGGER.warning("command failed with returncode %d", status)
        else:
            LOGGER.warning("command failed with returncode %d: %s", status, command)

        return None
    finally:
        if proc.returncode is None:
            proc.kill()
