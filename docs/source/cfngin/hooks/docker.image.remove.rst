###################
docker.image.remove
###################

:Hook Path: ``runway.cfngin.hooks.docker.image.remove``


Docker image remove hook.

Replicates the functionality of the ``docker image remove`` CLI command.

.. versionadded:: 1.18.0



****
Args
****

.. data:: ecr_repo
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

  .. data:: aws_region
    :type: str | None
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

  .. data:: registry_alias
    :type: str | None
    :value: None
    :noindex:

    If it is a public repository, provide the alias.

  .. data:: repo_name
    :type: str
    :noindex:

    The name of the repository.

.. data:: force
  :type: bool
  :value: False
  :noindex:

  Whether to force the removal of the image.

.. data:: image
  :type: DockerImage | None
  :value: None
  :noindex:

  A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object.
  This can be retrieved from ``hook_data`` for a preceding :ref:`docker.image.build hook` using the
  :ref:`hook_data Lookup <hook_data lookup>`.

  If providing a value for this field, do not provide a value for ``ecr_repo`` or ``repo``.

.. data:: noprune
  :type: bool
  :value: False
  :noindex:

  Whether to delete untagged parents.

.. data:: repo
  :type: str | None
  :value: None
  :noindex:

  URI of a non Docker Hub repository where the image will be stored.
  If providing one of the other repo values or ``image``, leave this value empty.

.. data:: tags
  :type: list[str]
  :value: ["latest"]
  :noindex:

  List of tags to remove.



*******
Example
*******

.. code-block:: yaml

  pre_deploy:
    - path: runway.cfngin.hooks.docker.login
      args:
        ecr: true
        password: ${ecr login-password}
    - path: runway.cfngin.hooks.docker.image.build
      args:
        ecr_repo:
          repo_name: ${cfn ${namespace}-test-ecr.Repository}
        tags:
          - latest
          - python3.9
    - path: runway.cfngin.hooks.docker.image.push
      args:
        image: ${hook_data docker.image}
        tags:
          - latest
          - python3.9

  stacks:
    ...

  post_deploy:
    - path: runway.cfngin.hooks.docker.image.remove
      args:
        image: ${hook_data docker.image}
        tags:
          - latest
          - python3.9
