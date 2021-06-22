.. _cfngin-hooks:

#####
Hooks
#####

A :class:`~cfngin.hook` is a python function, class, or class method that is executed before or after an action is taken for the entire config.

Only the following actions allow pre/post hooks:

:deploy:
  using fields :attr:`~cfngin.config.pre_deploy` and :attr:`~cfngin.config.post_deploy`
:destroy:
  using fields :attr:`~cfngin.config.pre_destroy` and :attr:`~cfngin.config.post_destroy`

.. class:: cfngin.hook

  When defining a hook in one of the supported fields, the follow fields can be used.

  .. rubric:: Lookup Support

  The following fields support lookups:

  - :attr:`~cfngin.hook.args`

  .. attribute:: args
    :type: Optional[Dict[str, Any]]
    :value: {}

    A dictionary of arguments to pass to the hook.

    This field supports the use of :ref:`lookups <cfngin-lookups>`.

    .. important::
      :ref:`Lookups <cfngin-lookups>` that change the order of execution, like :ref:`output <output lookup>`, can only be used in a *post* hook but hooks like :ref:`rxref <xref lookup>` are able to be used with either *pre* or *post* hooks.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - args:
            key: ${val}

  .. attribute:: data_key
    :type: Optional[str]
    :value: None

    If set, and the hook returns data (a dictionary), the results will be stored in :attr:`CfnginContext.hook_data <runway.context.CfnginContext.hook_data>` with the ``data_key`` as its key.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - data_key: example-key

  .. attribute:: enabled
    :type: Optional[bool]
    :value: True

    Whether to execute the hook every CFNgin run.
    This field provides the ability to execute a hook per environment when combined with a variable.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - enabled: ${enable_example_hook}

  .. attribute:: path
    :type: str

    Python importable path to the hook.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - path: runway.cfngin.hooks.command.run_command

  .. attribute:: required
    :type: Optional[bool]
    :value: True

    Whether to stop execution if the hook fails.


.. contents::
  :depth: 4


----


**************
Built-in Hooks
**************

acm.Certificate
===============

.. rubric:: Requirements

- Route 53 hosted zone

  - authoritative for the domain the certificate is being created for
  - in the same AWS account as the certificate being created


.. rubric:: Description

Manage a DNS validated certificate in AWS Certificate Manager.

When used in the :attr:`~cfngin.config.pre_deploy` or :attr:`~cfngin.config.post_deploy` stage this hook will create a CloudFormation stack containing a DNS validated certificate.
It will automatically create a record in Route 53 to validate the certificate and wait for the stack to complete before returning the ``CertificateArn`` as hook data.
The CloudFormation stack also outputs the ARN of the certificate as ``CertificateArn`` so that it can be referenced from other stacks.

When used in the :attr:`~cfngin.config.pre_destroy` or :attr:`~cfngin.config.post_destroy` stage this hook will delete the validation record from Route 53 then destroy the stack created during a deploy stage.

If the hook fails during a deploy stage (e.g. stack rolls back or Route 53 can't be updated) all resources managed by this hook will be destroyed.
This is done to avoid orphaning resources/record sets which would cause errors during subsequent runs.
Resources effected include the CloudFormation stack it creates, ACM certificate, and Route 53 validation record.

.. rubric:: Hook Path

:class:`runway.cfngin.hooks.acm.Certificate`


.. rubric:: Args
.. data:: alt_names
  :type: Optional[List[str]]
  :value: []
  :noindex:

  Additional FQDNs to be included in the Subject Alternative Name extension of the ACM certificate.
  For example, you can add *www.example.net* to a certificate for which the ``domain`` field is
  *www.example.com* if users can reach your site by using either name.

.. data:: domain
  :type: str
  :noindex:

  The fully qualified domain name (FQDN), such as *www.example.com*, with which you want to secure an ACM certificate.
  Use an asterisk (``*``) to create a wildcard certificate that protects several sites in the same domain.
  For example, *\*.example.com* protects *www.example.com*, *site.example.com*, and *images.example.com*.

.. data:: hosted_zone_id
  :type: str
  :noindex:

  The ID of the Route 53 Hosted Zone that contains the resource record sets that you want to change.
  This must exist in the same account that the certificate will be created in.

.. data:: stack_name
  :type: Optional[str]
  :value: None
  :noindex:

  Provide a name for the stack used to create the certificate.
  If not provided, the domain is used (replacing ``.`` with ``-``).
  If the is provided in a deploy stage, its needs to be provided in the matching destroy stage.

.. data:: ttl
  :type: Optional[int]
  :value: None
  :noindex:

  The resource record cache time to live (TTL), in seconds. (*default:* ``300``)



.. rubric:: Example
.. code-block:: yaml

    namespace: example
    cfngin_bucket: ''

    sys_path: ./

    pre_deploy:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}

    stack:
      sampleapp:
        class_path: blueprints.sampleapp.BlueprintClass
        variables:
          cert_arn: ${rxref www-example-com::CertificateArn}

    post_destroy:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}


.. versionadded:: 1.6.0


----


.. _aws_lambda hook:

aws_lambda.upload_lambda_functions
==================================

.. rubric:: Description

Build Lambda payloads from user configuration and upload them to S3 using the following process:

#. Constructs ZIP archives containing files matching specified patterns for each function.
#. Uploads the result to Amazon S3
#. Returns a |Dict| of "*function name*: :class:`troposphere.awslambda.Code`".

The returned value can retrieved using the :ref:`hook_data Lookup <hook_data lookup>` or by interacting with the :class:`~runway.context.CfnginContext` object passed to the |Blueprint|.

Configuration consists of some global options, and a dictionary of function specifications.
In the specifications, each key indicating the name of the function (used for generating names for artifacts), and the value determines what files to include in the ZIP (see more details below).

If a ``requirements.txt`` file or ``Pipfile/Pipfile.lock`` files are found at the root of the provided ``path``, the hook will use the appropriate method to package dependencies with your source code automatically.
If you want to explicitly use ``pipenv`` over ``pip``, provide ``use_pipenv: true`` for the function.

Docker can be used to collect python dependencies instead of using system python to build appropriate binaries for Lambda.
This can be done by including the ``dockerize_pip`` configuration option which can have a value of ``true`` or ``non-linux``.

Payloads are uploaded to either the |cfngin_bucket| or an explicitly specified bucket, with the object key containing it's checksum to allow repeated uploads to be skipped in subsequent runs.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.aws_lambda.upload_lambda_functions`


.. rubric:: Args
.. data:: bucket
  :type: Optional[str]
  :value: None
  :noindex:

  Custom bucket to upload functions to. If not provided, |cfngin_bucket| will be used.

.. data:: bucket_region
  :type: Optional[str]
  :value: None
  :noindex:

  The region in which the bucket should exist.
  If not provided, :attr:`~cfngin.config.cfngin_bucket_region` will be used.

.. data:: prefix
  :type: Optional[str]
  :value: None
  :noindex:

  S3 key prefix to prepend to the uploaded zip name.

.. data:: follow_symlinks
  :type: Optional[bool]
  :value: False
  :noindex:

  Whether symlinks should be followed and included with the zip artifact.

.. data:: payload_acl
  :type: runway.cfngin.hooks.aws_lambda.PayloadAclTypeDef
  :value: private
  :noindex:

  The canned S3 object ACL to be applied to the uploaded payload.

.. data:: functions
  :type: Dict[str, Any]
  :noindex:

  Configurations of desired payloads to build.
  Keys correspond to function names, used to derive key names for the payload.
  Each value should itself be a dictionary, with the following data:

  .. data:: docker_file
    :type: Optional[str]
    :value: None
    :noindex:

    Path to a local DockerFile that will be built and used for ``dockerize_pip``.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: docker_image
    :type: Optional[str]
    :value: None
    :noindex:

    Custom Docker image to use  with ``dockerize_pip``.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: dockerize_pip
    :type: Optional[Union[bool, Literal["non-linux"]]]
    :value: None
    :noindex:

    Whether to use Docker when restoring dependencies with pip.
    Can be set to ``true``/``false`` or the special string ``non-linux`` which will only run on non Linux systems.
    To use this option Docker must be installed.

  .. data:: exclude
    :type: Optional[Union[List[str], str]]
    :value: None
    :noindex:

    Pattern or list of patterns of files to exclude from the payload.
    If provided, any files that match will be ignored, regardless of whether they match an inclusion pattern.

    Commonly ignored files are already excluded by default, such as ``.git``, ``.svn``, ``__pycache__``, ``*.pyc``, ``.gitignore``, etc.

  .. data:: include
    :type: Optional[List[str], str]
    :value: None
    :noindex:

    Pattern or list of patterns of files to include in the payload.
    If provided, only files that match these patterns will be included in the payload.

    Omitting it is equivalent to accepting all files that are not otherwise excluded.

  .. data:: path
    :type: str
    :noindex:

    Base directory of the Lambda function payload content.
    If it not an absolute path, it will be considered relative to the directory containing the CFNgin configuration file in use.

    Files in this directory will be added to the payload ZIP, according to the include and exclude patterns.
    If no patterns are provided, all files in this directory (respecting default exclusions) will be used.

    Files are stored in the archive with path names relative to this directory.
    So, for example, all the files contained directly under this directory will be added to the root of the ZIP file.

  .. data:: python_path
    :type: Optional[str]
    :value: None
    :noindex:

    Absolute path to a python interpreter to use for ``pip``/``pipenv`` actions.
    If not provided, the current python interpreter will be used for ``pip`` and ``pipenv`` will be used from the current ``$PATH``.

  .. data:: runtime
    :type: Optional[str]
    :value: None
    :noindex:

    Runtime of the AWS Lambda Function being uploaded.
    Used with ``dockerize_pip`` to automatically select the appropriate Docker image to use.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: use_pipenv
    :type: Optional[bool]
    :value: False
    :noindex:

    Will determine if pipenv will be used to generate requirements.txt from an existing Pipfile.
    To use this option pipenv must be installed.


.. rubric:: Example
.. code-block:: yaml
  :caption: Hook Configuration

  pre_deploy:
    - path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
      required: true
      enabled: true
      data_key: lambda
      args:
        bucket: custom-bucket
        follow_symlinks: true
        prefix: cloudformation-custom-resources/
        payload_acl: authenticated-read
        functions:
          MyFunction:
            path: ./lambda_functions
            dockerize_pip: non-linux
            use_pipenv: true
            runtime: python3.8
            include:
              - '*.py'
              - '*.txt'
            exclude:
              - '*.pyc'
              - test/

.. code-block:: python
  :caption: Blueprint Usage

  """Example Blueprint."""
  from __future__ import annotations

  from typing import cast

  from troposphere.awslambda import Code, Function

  from runway.cfngin.blueprints.base import Blueprint


  class LambdaBlueprint(Blueprint):
      """Example Blueprint."""

      def create_template(self) -> None:
          """Create a template from the blueprint."""
          code = cast(Code, self.context.hook_data["lambda"]["MyFunction"])

          self.template.add_resource(
              Function(
                  "MyFunction",
                  Code=code,
                  Handler="my_function.handler",
                  Role="...",
                  Runtime="python3.8",
              )
          )


----


build_staticsite.build
======================

.. rubric:: Description

Build static site. Used by the :ref:`Static Site <staticsite>` module type.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.staticsite.build_staticsite.build`


.. rubric:: Args

See :ref:`Static Site <staticsite>` module documentation for details.

.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.


cleanup_s3.purge_bucket
=======================

.. rubric:: Description

Delete objects in a Bucket.
Primarily used as a :attr:`~cfngin.config.pre_destroy` hook before deleting an S3 bucket.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.cleanup_s3.purge_bucket`


.. rubric:: Args
.. data:: bucket_name
  :type: str
  :noindex:

  Name of the S3 bucket.

.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.


cleanup_ssm.delete_param
========================

.. rubric:: Description

Delete SSM parameter.
Primarily used when an SSM parameter is created by a hook rather than CloudFormation.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.cleanup_ssm.delete_param`


.. rubric:: Args
.. data:: parameter_name
  :type: str
  :noindex:

  Name of an SSM parameter.

.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.


command.run_command
===================

.. rubric:: Description

Run a shell custom command as a hook.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.command.run_command`


.. rubric:: Args
.. data:: command
  :type: Union[List[str], str]
  :noindex:

  Command(s) to run.

.. data:: capture
  :type: Optional[bool]
  :value: False
  :noindex:

  If enabled, capture the command's stdout and stderr, and return them in the hook result.

.. data:: interactive
  :type: Optional[bool]
  :value: False
  :noindex:

  If enabled, allow the command to interact with stdin.
  Otherwise, stdin will be set to the null device.

.. data:: ignore_status
  :type: Optional[bool]
  :value: False
  :noindex:

  Don't fail the hook if the command returns a non-zero status.

.. data:: quiet
  :type: Optional[bool]
  :value: False
  :noindex:

  Redirect the command's stdout and stderr to the null device, silencing all output.
  Should not be enabled if ``capture`` is also enabled.

.. data:: stdin
  :type: Optional[str]
  :value: None
  :noindex:

  String to send to the stdin of the command.
  Implicitly disables ``interactive``.

.. data:: env
  :type: Optional[Dict[str, str]]
  :value: None
  :noindex:

  Dictionary of environment variable overrides for the command context.
  Will be merged with the current environment.

.. data:: **kwargs
  :type: Any
  :noindex:

  Any other arguments will be forwarded to the :class:`subprocess.Popen` function.
  Interesting ones include: ``cwd`` and ``shell``.


.. rubric:: Example
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


----


.. _cfngin.hooks.docker:

docker
======

A collection of hooks that interact with Docker.

docker.image.build
------------------

.. rubric:: Description

Docker image build hook.

Replicates the functionality of the ``docker image build`` CLI command.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.docker.image.build`

.. rubric:: Args
.. data:: docker
  :type: Optional[Dict[str, Any]]
  :value: {}
  :noindex:

  Options for ``docker image build``.

  .. data:: buildargs
    :type: Optional[Dict[str, str]]
    :value: None
    :noindex:

    Dict of build-time variables.

  .. data:: custom_context
    :type: bool
    :value: False
    :noindex:

    Optional if providing a path to a zip file.

  .. data:: extra_hosts
    :type: Optional[Dict[str, str]]
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
    :type: Optional[str]
    :value: None
    :noindex:

    Isolation technology used during build.

  .. data: network_mode
    :type: Optional[str]
    :value: None
    :noindex:

    Network mode for the run commands during build.

  .. data:: nocache
    :type: bool
    :value: False
    :noindex:

    Don't use cache when set to ``True``.

  .. data:: platform
    :type: Optional[str]
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
    :type: Optional[str]
    :value: None
    :noindex:

    Optional name and tag to apply to the base image when it is built.

  .. data:: target
    :type: Optional[str]
    :value: None
    :noindex:

    Name of the build-stage to build in a multi-stage Dockerfile.

  .. data:: timeout
    :type: Optional[int]
    :value: None
    :noindex:

    HTTP timeout.

  .. data:: use_config_proxy
    :type: bool
    :value: False
    :noindex:

    If ``True`` and if the docker client configuration file (``~/.docker/config.json`` by default) contains a proxy configuration, the corresponding environment variables will be set in the container being built.

.. data:: dockerfile
  :type: Optional[str]
  :value: "./Dockerfile"
  :noindex:

  Path within the build context to the Dockerfile.

.. data:: ecr_repo
  :type: Optional[Dict[str, Optional[str]]]
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo``.

  If using a private registry, only ``repo_name`` is required.
  If using a public registry, ``repo_name`` and ``registry_alias``.

  .. data:: account_id
    :type: Optional[str]
    :value: None
    :noindex:

    AWS account ID that owns the registry being logged into. If not provided,
    it will be acquired automatically if needed.

  .. data:: aws_region
    :type: Optional[str]
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

  .. data:: registry_alias
    :type: Optional[str]
    :value: None
    :noindex:

    If it is a public repository, provide the alias.

  .. data:: repo_name
    :type: str
    :noindex:

    The name of the repository.

.. data:: path
  :type: Optional[str]
  :noindex:

  Path to the directory containing the Dockerfile.

.. data:: repo
  :type: Optional[str]
  :value: None
  :noindex:

  URI of a non Docker Hub repository where the image will be stored.
  If providing one of the other repo values, leave this value empty.

.. data:: tags
  :type: Optional[List[str]]
  :value: ["latest"]
  :noindex:

  List of tags to apply to the image.

.. rubric:: Returns

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

.. versionadded:: 1.18.0


docker.image.push
-----------------

.. rubric:: Description

Docker image push hook.

Replicates the functionality of the ``docker image push`` CLI command.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.docker.image.push`

.. rubric:: Args
.. data:: ecr_repo
  :type: Optional[Dict[str, Optional[str]]]
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo`` or ``image``.

  If using a private registry, only ``repo_name`` is required.
  If using a public registry, ``repo_name`` and ``registry_alias``.

  .. data:: account_id
    :type: Optional[str]
    :value: None
    :noindex:

    AWS account ID that owns the registry being logged into. If not provided,
    it will be acquired automatically if needed.

  .. data:: aws_region
    :type: Optional[str]
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

  .. data:: registry_alias
    :type: Optional[str]
    :value: None
    :noindex:

    If it is a public repository, provide the alias.

  .. data:: repo_name
    :type: str
    :noindex:

    The name of the repository.

.. data:: image
  :type: Optional[DockerImage]
  :value: None
  :noindex:

  A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object.
  This can be retrieved from ``hook_data`` for a preceding `docker.image.build`_ using the
  :ref:`hook_data Lookup <hook_data lookup>`.

  If providing a value for this field, do not provide a value for ``ecr_repo`` or ``repo``.

.. data:: repo
  :type: Optional[str]
  :value: None
  :noindex:

  URI of a non Docker Hub repository where the image will be stored.
  If providing one of the other repo values or ``image``, leave this value empty.

.. data:: tags
  :type: Optional[List[str]]
  :value: ["latest"]
  :noindex:

  List of tags to push.

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

  stacks:
    ecr-lambda-function:
      class_path: blueprints.EcrFunction
      variables:
        ImageUri: ${hook_data docker.image.uri.latest}

.. versionadded:: 1.18.0


docker.image.remove
-------------------

.. rubric:: Description

Docker image remove hook.

Replicates the functionality of the ``docker image remove`` CLI command.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.docker.image.remove`

.. rubric:: Args
.. data:: ecr_repo
  :type: Optional[Dict[str, Optional[str]]]
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo`` or ``image``.

  If using a private registry, only ``repo_name`` is required.
  If using a public registry, ``repo_name`` and ``registry_alias``.

  .. data:: account_id
    :type: Optional[str]
    :value: None
    :noindex:

    AWS account ID that owns the registry being logged into. If not provided,
    it will be acquired automatically if needed.

  .. data:: aws_region
    :type: Optional[str]
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

  .. data:: registry_alias
    :type: Optional[str]
    :value: None
    :noindex:

    If it is a public repository, provide the alias.

  .. data:: repo_name
    :type: str
    :noindex:

    The name of the repository.

.. data:: force
  :type: Optional[bool]
  :value: False
  :noindex:

  Whether to force the removal of the image.

.. data:: image
  :type: Optional[DockerImage]
  :value: None
  :noindex:

  A :class:`~runway.cfngin.hooks.docker.data_models.DockerImage` object.
  This can be retrieved from ``hook_data`` for a preceding `docker.image.build`_ using the
  :ref:`hook_data Lookup <hook_data lookup>`.

  If providing a value for this field, do not provide a value for ``ecr_repo`` or ``repo``.

.. data:: noprune
  :type: Optional[bool]
  :value: False
  :noindex:

  Whether to delete untagged parents.

.. data:: repo
  :type: Optional[str]
  :value: None
  :noindex:

  URI of a non Docker Hub repository where the image will be stored.
  If providing one of the other repo values or ``image``, leave this value empty.

.. data:: tags
  :type: Optional[List[str]]
  :value: ["latest"]
  :noindex:

  List of tags to remove.

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

.. versionadded:: 1.18.0


docker.login
------------

.. rubric:: Description

Docker login hook.

Replicates the functionality of the ``docker login`` CLI command.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.docker.login`

.. rubric:: Args
.. data:: dockercfg_path
  :type: Optional[str]
  :value: None
  :noindex:

  Use a custom path for the Docker config file (``$HOME/.docker/config.json`` if present, otherwise ``$HOME/.dockercfg``).

.. data:: ecr
  :type: Optional[Dict[str, Optional[str]]]
  :value: None
  :noindex:

  Information describing an ECR repository. This is used to construct the repository URL.
  If providing a value for this field, do not provide a value for ``repo`` or ``image``.

  If using a private registry, only ``repo_name`` is required.
  If using a public registry, ``repo_name`` and ``registry_alias``.

  .. data:: account_id
    :type: Optional[str]
    :value: None
    :noindex:

    AWS account ID that owns the registry being logged into. If not provided,
    it will be acquired automatically if needed.

  .. data:: alias
    :type: Optional[str]
    :value: None
    :noindex:

    If it is a public registry, provide the alias.

  .. data:: aws_region
    :type: Optional[str]
    :value: None
    :noindex:

    AWS region where the registry is located. If not provided, it will be acquired
    automatically if needed.

.. data:: email
  :type: Optional[str]
  :value: None
  :noindex:

  The email for the registry account.

.. data:: password
  :type: str
  :noindex:

  The plaintext password for the registry account.

.. data:: registry
  :type: Optional[str]
  :value: None
  :noindex:

  URL to the registry (e.g. ``https://index.docker.io/v1/``).

  If providing a value for this field, do not provide a value for ``ecr``.

.. data:: username
  :type: Optional[str]
  :value: None
  :noindex:

  The registry username. Defaults to ``AWS`` if supplying ``ecr``.

.. rubric:: Example
.. code-block:: yaml

  pre_deploy:
    - path: runway.cfngin.hooks.docker.login
      args:
        ecr: true
        password: ${ecr login-password}

.. versionadded:: 1.18.0


ecr.purge_repository
====================

.. rubric:: Description

Purge all images from an ECR repository.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.ecr.purge_repository`

.. rubric:: Args
.. data:: repository_name
  :type: str
  :noindex:

  The name of the ECR repository to purge.

.. rubric:: Example
.. code-block:: yaml

  pre_destroy:
    - path: runway.cfngin.hooks.ecr.purge_repository
      args:
        repository_name: example-repo

.. versionadded:: 1.18.0


----


ecs.create_clusters
===================

.. rubric:: Description

Create ECS clusters.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.ecs.create_clusters`


.. rubric:: Args

.. data:: clusters
  :type: List[str]
  :noindex:

  Names of clusters to create.


----


iam.create_ecs_service_role
===========================

.. rubric:: Description

Create ecsServiceRole IAM role.

.. seealso::
  `AWS Documentation describing the Role <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using-service-linked-roles.html>`__

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.iam.create_ecs_service_role`

.. rubric:: Args
.. data:: role_name
  :type: Optional[str]
  :value: "ecsServiceRole"
  :noindex:

  Name of the role to create.


----


iam.ensure_server_cert_exists
=============================

.. rubric:: Description

Ensure server certificate exists.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.iam.ensure_server_cert_exists`

.. rubric:: Args
.. data:: cert_name
  :type: str
  :noindex:

  Name of the certificate that should exist.

.. data:: prompt
  :type: bool
  :value: True
  :noindex:

  Whether to prompt to upload a certificate if one does not exist.


----


keypair.ensure_keypair_exists
=============================

.. rubric:: Description

Ensure a specific keypair exists within AWS. If the key doesn't exist, upload it.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.keypair.ensure_keypair_exists`


.. rubric:: Args
.. data:: keypair
  :type: str
  :noindex:

  Name of the key pair to create

.. data:: public_key_path
  :type: Optional[str]
  :value: None
  :noindex:

  Path to a public key file to be imported instead of generating a new key.
  Incompatible with the SSM options, as the private key will not be available for storing.

.. data:: ssm_key_id
  :type: Optional[str]
  :value: None
  :noindex:

  ID of a KMS key to encrypt the SSM
  parameter with. If omitted, the default key will be used.

.. data:: ssm_parameter_name
  :type: Optional[str]
  :value: None
  :noindex:

  Path to an SSM store parameter to receive the generated private key, instead of importing it or storing it locally.


----


route53.create_domain
=====================

.. rubric:: Description

Create a domain within route53.

.. rubric:: Hook Path

:func:`runway.cfngin.hooks.route53.create_domain`


.. rubric:: Args
.. data:: domain
  :type: str
  :noindex:

  Domain name for the Route 53 hosted zone to be created.


----


ssm
===

A collection of hooks that interact with AWS SSM.


ssm.parameter.SecureString
--------------------------

.. rubric:: Description

Create, update, and delete a **SecureString** SSM parameter.

A SecureString parameter is any sensitive data that needs to be stored and referenced in a secure manner.
If you have data that you don't want users to alter or reference in plaintext, such as passwords or license keys, create those parameters using the SecureString datatype.

When used in the :attr:`~cfngin.config.pre_deploy` or :attr:`~cfngin.config.post_deploy` stage this hook will create or update an SSM parameter.

When used in the :attr:`~cfngin.config.pre_destroy` or :attr:`~cfngin.config.post_destroy` stage this hook will delete an SSM parameter.

.. rubric:: Hook Path

:class:`runway.cfngin.hooks.ssm.parameter.SecureString`

.. rubric:: Args
.. data:: allowed_pattern
  :type: Optional[str]
  :value: None
  :noindex:

  A regular expression used to validate the parameter value.

.. data:: data_type
  :type: Optional[Literal["aws:ec2:image", "text"]]
  :value: None
  :noindex:

  The data type for a String parameter.
  Supported data types include plain text and Amazon Machine Image IDs.

.. data:: description
  :type: Optional[str]
  :value: None
  :noindex:

  Information about the parameter.

.. data:: force
  :type: bool
  :value: False
  :noindex:

  Skip checking the current value of the parameter, just put it.
  Can be used alongside **overwrite** to always update a parameter.

.. data:: key_id
  :type: Optional[str]
  :value: None
  :noindex:

  The KMS Key ID that you want to use to encrypt a parameter.
  Either the default AWS Key Management Service (AWS KMS) key automatically assigned to your AWS account or a custom key.

.. data:: name
  :type: str
  :noindex:

  The fully qualified name of the parameter that you want to add to the system.

.. data:: overwrite
  :type: bool
  :value: True
  :noindex:

  Allow overwriting an existing parameter.
  If this is set to ``False`` and the parameter already exists, the parameter will not be updated and a warning will be logged.

.. data:: policies
  :type: Optional[Union[List[Dict[str, Any]], str]]
  :value: None
  :noindex:

  One or more policies to apply to a parameter.
  This field takes a JSON array.

.. data:: tags
  :type: Optional[Union[Dict[str, str], List[TagTypeDef]]]
  :value: None
  :noindex:

  Tags to be applied to the parameter.

.. data:: tier
  :type: Literal["Advanced", "Intelligent-Tiering", "Standard"]
  :value: "Standard"
  :noindex:

  The parameter tier to assign to a parameter.

.. data:: value
  :type: Optional[str]
  :value: None
  :noindex:

  The parameter value that you want to add to the system.
  Standard parameters have a value limit of 4 KB.
  Advanced parameters have a value limit of 8 KB.

  If the value of this field is falsy, the parameter will not be created or updated.

  If the value of this field matches what is already in SSM Parameter Store, it will not be updated unless **force** is ``True``.

.. rubric:: Example
.. code-block:: yaml

  pre_deploy: &hooks
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/foo
        value: bar
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/parameter1
        description: This is an example.
        tags:
          tag-key: tag-value
        tier: Advanced
        value: ${value_may_be_none}
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/parameter2
        policies:
          - Type: Expiration
            Version: 1.0
            Attributes:
              Timestamp: 2018-12-02T21:34:33.000Z
        tags:
          - Key: tag-key
            Value: tag-value
        value: ${something_else}

  post_destroy: *hooks

.. versionadded:: 2.2.0


----


upload_staticsite.sync
======================

.. rubric:: Description

Sync static website to S3 bucket. Used by the :ref:`Static Site <staticsite>` module type.


.. rubric:: Hook Path

:func:`runway.cfngin.hooks.staticsite.upload_staticsite.sync`


.. rubric:: Args

See :ref:`Static Site <staticsite>` module documentation for details.

.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.


----


*********************
Writing A Custom Hook
*********************

A custom hook must be in an executable, importable python package or standalone file.
The hook must be importable using your current ``sys.path``.
This takes into account the :attr:`~cfngin.config.sys_path` defined in the :class:`~cfngin.config` file as well as any ``paths`` of :attr:`~cfngin.config.package_sources`.

The hook must accept a minimum of two arguments, ``context`` and ``provider``.
Aside from the required arguments, it can have any number of additional arguments or use ``**kwargs`` to accept anything passed to it.
The values for these additional arguments come from the :attr:`~cfngin.hook.args` field of the hook definition.

The hook must return ``True`` or a truthy object if it was successful.
It must return ``False`` or a falsy object if it failed.
This signifies to CFNgin whether or not to halt execution if the hook is :attr:`~cfngin.hook.required`.
If a |Dict| or :class:`~cfngin.utils.MutableMap` is returned, it can be accessed by subsequent hooks, lookups, or Blueprints from the context object.
It will be stored as ``context.hook_data[data_key]`` where :attr:`~cfngin.hook.data_key` is the value set in the hook definition.
If :attr:`~cfngin.hook.data_key` is not provided or the type of the returned data is not a |Dict| or :class:`~cfngin.utils.MutableMap`, it will not be added to the context object.

If using boto3 in a hook, use :meth:`context.get_session() <runway.context.CfnginContext.get_session>` instead of creating a new session to ensure the correct credentials are used.

.. code-block:: python

  """context.get_session() example."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, Any

  if TYPE_CHECKING:
      from runway.context import CfnginContext


  def do_something(context: CfnginContext, **_kwargs: Any) -> None:
      """Do something."""
      s3_client = context.get_session().client("s3")


Example Hook Function
=====================

.. code-block:: python
  :caption: local_path/hooks/my_hook.py

  """My hook."""
  from __future__ import annotations

  from typing import Dict, Optional


  def do_something(*, is_failure: bool = True, **kwargs: str) -> Optional[Dict[str, str]]:
      """Do something."""
      if is_failure:
          return None
      return {"result": f"You are not a failure {kwargs.get('name', 'Kevin')}."}

.. code-block:: yaml
  :caption: local_path/cfngin.yaml

  namespace: example
  sys_path: ./

  pre_deploy:
    - path: hooks.my_hook.do_something
      args:
        is_failure: false


Example Hook Class
==================

.. code-block:: python
  :caption: local_path/hooks/my_hook.py

  """My hook."""
  import logging
  from typing import Dict, Optional

  from runway.cfngin.hooks.base import Hook

  LOGGER = logging.getLogger(__name__)


  class MyClass(Hook):
      """My class does a thing.

      Keyword Args:
          is_failure (bool): Force the hook to fail if true.
          name (str): Name used in the response.

      Returns:
          Dict[str, str]: Response message is stored in ``result``.

      Example:
      .. code-block:: yaml

          pre_deploy:
            - path: hooks.my_hook.MyClass
              args:
              is_failure: False
              name: Karen

      """

      def post_deploy(self) -> Optional[Dict[str, str]]:
          """Run during the **post_deploy** stage."""
          if self.args["is_failure"]:
              return None
          return {"result": f"You are not a failure {self.args['name']}."}

      def post_destroy(self) -> None:
          """Run during the **post_destroy** stage."""
          LOGGER.error("post_destroy is not supported by this hook")

      def pre_deploy(self) -> None:
          """Run during the **pre_deploy** stage."""
          LOGGER.error("pre_deploy is not supported by this hook")

      def pre_destroy(self) -> None:
          """Run during the **pre_destroy** stage."""
          LOGGER.error("pre_destroy is not supported by this hook")

.. code-block:: yaml
  :caption: local_path/cfngin.yaml

  namespace: example
  sys_path: ./

  pre_deploy:
    - path: hooks.my_hook.MyClass
      args:
        is_failure: False
        name: Karen
