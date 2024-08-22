.. _docker.login hook:

############
docker.login
############

:Hook Path: ``runway.cfngin.hooks.docker.login``


Docker login hook.

Replicates the functionality of the ``docker login`` CLI command.

.. versionadded:: 1.18.0



****
Args
****

.. data:: dockercfg_path
  :type: str | None
  :value: None
  :noindex:

  Use a custom path for the Docker config file (``$HOME/.docker/config.json`` if present, otherwise ``$HOME/.dockercfg``).

.. data:: ecr
  :type: dict[str, str | None] | None
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo`` or ``image``.

  If using a private registry, only ``repo_name`` is required.
  If using a public registry, ``repo_name`` and ``registry_alias``.

  .. data:: account_id
    :type: str | None
    :value: None
    :noindex:

    AWS account ID that owns the registry being logged into. If not provided,
    it will be acquired automatically if needed.

  .. data:: alias
    :type: str | None
    :value: None
    :noindex:

    If it is a public registry, provide the alias.

  .. data:: aws_region
    :type: str | None
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

.. data:: email
  :type: str | None
  :value: None
  :noindex:

  The email for the registry account.

.. data:: password
  :type: str
  :noindex:

  The plaintext password for the registry account.

.. data:: registry
  :type: str | None
  :value: None
  :noindex:

  URL to the registry (e.g. ``https://index.docker.io/v1/``).

  If providing a value for this field, do not provide a value for ``ecr``.

.. data:: username
  :type: str | None
  :value: None
  :noindex:

  The registry username. Defaults to ``AWS`` if supplying ``ecr``.



*******
Example
*******

.. code-block:: yaml

  pre_deploy:
    - path: runway.cfngin.hooks.docker.login
      args:
        ecr: true
        password: ${ecr login-password}
