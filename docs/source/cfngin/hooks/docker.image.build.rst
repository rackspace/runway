.. _docker.image.build hook:

##################
docker.image.build
##################

:Hook Path: ``runway.cfngin.hooks.docker.image.build``


Docker image build hook.

Replicates the functionality of the ``docker image build`` CLI command.


.. versionadded:: 1.18.0



****
Args
****

.. data:: docker
  :type: dict[str, Any]
  :value: {}
  :noindex:

  Options for ``docker image build``.

  .. data:: buildargs
    :type: dict[str, str] | None
    :value: None
    :noindex:

    Dict of build-time variables.

  .. data:: custom_context
    :type: bool
    :value: False
    :noindex:

    Optional if providing a path to a zip file.

  .. data:: extra_hosts
    :type: dict[str, str] | None
    :value: None
    :noindex:

    Extra hosts to add to ``/etc/hosts`` in the building containers.
    Defined as a mapping of hostname to IP address.

  .. data:: forcerm
    :type: bool
    :value: False
    :noindex:

    Always remove intermediate containers, even after unsuccessful builds.

  .. data:: isolation
    :type: str | None
    :value: None
    :noindex:

    Isolation technology used during build.

  .. data:: network_mode
    :type: str | None
    :value: None
    :noindex:

    Network mode for the run commands during build.

  .. data:: nocache
    :type: bool
    :value: False
    :noindex:

    Don't use cache when set to ``True``.

  .. data:: platform
    :type: str | None
    :value: None
    :noindex:

    Set platform if server is multi-platform capable.
    Uses format ``os[/arch[/variant]]``.

  .. data:: pull
    :type: bool
    :value: False
    :noindex:

    Download any updates to the FROM image in the Dockerfile.

  .. data:: rm
    :type: bool
    :value: True
    :noindex:

    Remove intermediate containers.

  .. data:: squash
    :type: bool
    :value: False
    :noindex:

    Squash the resulting image layers into a single layer.

  .. data:: tag
    :type: str | None
    :value: None
    :noindex:

    Optional name and tag to apply to the base image when it is built.

  .. data:: target
    :type: str | None
    :value: None
    :noindex:

    Name of the build-stage to build in a multi-stage Dockerfile.

  .. data:: timeout
    :type: str | None
    :value: None
    :noindex:

    HTTP timeout.

  .. data:: use_config_proxy
    :type: bool
    :value: False
    :noindex:

    If ``True`` and if the docker client configuration file (``~/.docker/config.json`` by default) contains a proxy configuration, the corresponding environment variables will be set in the container being built.

.. data:: dockerfile
  :type: str | None
  :value: "./Dockerfile"
  :noindex:

  Path within the build context to the Dockerfile.

.. data:: ecr_repo
  :type: dict[str, str | None] | None
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo``.

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

.. data:: path
  :type: str | None
  :noindex:

  Path to the directory containing the Dockerfile.

.. data:: repo
  :type: str | None
  :value: None
  :noindex:

  URI of a non Docker Hub repository where the image will be stored.
  If providing one of the other repo values, leave this value empty.

.. data:: tags
  :type: list[str]
  :value: ["latest"]
  :noindex:

  List of tags to apply to the image.



*******
Returns
*******

:type:
  :class:`~runway.cfngin.hooks.docker.hook_data.DockerHookData`
:description:
  The value of item ``image`` in the returned object is set to the :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` that was just created.

The returned object is accessible with the :ref:`hook_data Lookup <hook_data lookup>` under the ``data_key`` of ``docker`` (do not specify a ``data_key`` for the hook, this is handled automatically).

.. important::
  Each execution of this hook overwrites any previous values stored in this attribute.
  It is advices to consume the resulting image object after it has been built, if it
  will be consumed by a later hook/stack.

.. rubric:: Example
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
