###################
command.run_command
###################

:Hook Path: ``runway.cfngin.hooks.command.run_command``


Run a shell custom command as a hook.



****
Args
****

.. data:: command
  :type: list[str] | str
  :noindex:

  Command(s) to run.

.. data:: capture
  :type: bool
  :value: False
  :noindex:

  If enabled, capture the command's stdout and stderr, and return them in the hook result.

.. data:: interactive
  :type: bool
  :value: False
  :noindex:

  If enabled, allow the command to interact with stdin.
  Otherwise, stdin will be set to the null device.

.. data:: ignore_status
  :type: bool
  :value: False
  :noindex:

  Don't fail the hook if the command returns a non-zero status.

.. data:: quiet
  :type: bool
  :value: False
  :noindex:

  Redirect the command's stdout and stderr to the null device, silencing all output.
  Should not be enabled if ``capture`` is also enabled.

.. data:: stdin
  :type: str | None
  :value: None
  :noindex:

  String to send to the stdin of the command.
  Implicitly disables ``interactive``.

.. data:: env
  :type: dict[str, str] | None
  :value: None
  :noindex:

  Dictionary of environment variable overrides for the command context.
  Will be merged with the current environment.

.. data:: **kwargs
  :type: Any
  :noindex:

  Any other arguments will be forwarded to the :class:`subprocess.Popen` function.
  Interesting ones include: ``cwd`` and ``shell``.



*******
Example
*******

.. code-block:: yaml

    pre_deploy:
      - path: runway.cfngin.hooks.command.run_command
        required: true
        enabled: true
        data_key: copy_env
        args:
          command: ['cp', 'environment.template', 'environment']
      - path: runway.cfngin.hooks.command.run_command
        required: true
        enabled: true
        data_key: get_git_commit
        args:
          command: ['git', 'rev-parse', 'HEAD']
          cwd: ./my-git-repo
          capture: true
      - path: runway.cfngin.hooks.command.run_command
        args:
          command: '`cd $PROJECT_DIR/project; npm install`'
          env:
            PROJECT_DIR: ./my-project
            shell: true
