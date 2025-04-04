##################
Runway Config File
##################

The Runway config file is where all options are defined.
It contains definitions for deployment and some global options that impact core functionality.

The Runway config file can have two possible names, ``runway.yml`` or ``runway.yaml``.
It must be stored at the root of the directory containing the modules to be deployed.

***********************
Top-Level Configuration
***********************

.. attribute:: deployments
  :type: list[deployment]

  A list of deployments that will be processed in the order they are defined.
  See Deployment_ for detailed information about defining this value.

  .. rubric:: Example
  .. code-block:: yaml

    deployments:
      - name: example
        modules:
          - sampleapp-01.cfn
          - path: sampleapp-02.cfn
        regions:
          - us-east-1

.. attribute:: ignore_git_branch
  :type: bool
  :value: false

  Optionally exclude the git branch name when determining the current :term:`Deploy Environment`.

  This can be useful when using the directory name or environment variable to set the :term:`Deploy Environment` to ensure the correct value is used.

  .. rubric:: Example
  .. code-block:: yaml

    ignore_git_branch: true

  .. note:: The existence of ``DEPLOY_ENVIRONMENT`` in the environment will automatically ignore the git branch.

.. attribute:: runway_version
  :type: str | None
  :value: None

  Define the versions of Runway that can be used with this configuration file.

  The value should be a `PEP 440 <https://www.python.org/dev/peps/pep-0440/>`__ compliant version specifier set.

  .. rubric:: Example
  .. code-block:: yaml
    :caption: greater than or equal to 1.14.0

    runway_version: ">=1.14.0"

  .. code-block:: yaml
    :caption: explicit version

    runway_version: "==14.0.0"

  .. code-block:: yaml
    :caption: greater than or equal to 1.14.0 but less than 2.0.0

    runway_version: ">=1.14.0,<2.0.0"  # or ~=1.14.0

  .. versionadded:: 1.11.0

.. _runway-variables:

.. attribute:: variables
  :type: dict[str, Any] | None
  :value: {}

  Runway variables are used to fill values that could change based on any number of circumstances.
  They can also be used to simplify the Runway config file by pulling lengthy definitions into another YAML file.
  Variables can be consumed in the config file by using the :ref:`var lookup <var-lookup>` in any field that supports :ref:`Lookups <Lookups>`.

  By default, Runway will look for and load a ``runway.variables.yml`` or ``runway.variables.yaml`` file that is in the same directory as the Runway config file.
  The file path and name of the file can optionally be defined in the config file.
  If the file path is explicitly provided and the file can't be found, an error will be raised.

  Variables can also be defined in the Runway config file directly.
  This can either be in place of a dedicated variables file, extend an existing file, or override values from the file.

  .. important::
    The :attr:`variables` and the variables file cannot contain lookups.
    If there is a lookup string in either of these locations, they will not be resolved.

  .. rubric:: Example
  .. code-block:: yaml

    deployments:
      - modules:
          - path: sampleapp.cfn
        env_vars: ${var env_vars}  # exists in example-file.yml
        parameters:
          namespace: ${var namespace}-${env DEPLOY_ENVIRONMENT}
        regions: ${var regions.${env DEPLOY_ENVIRONMENT}}

    variables:
      file_path: example-file.yml
      namespace: example
      regions:
        dev:
          - us-east-1
          - us-west-2

  .. versionadded 1.4.0

  .. data:: variables.file_path
    :type: str | None

    Explicit path to a variables file that will be loaded and merged with the variables defined here.

    .. rubric:: Example
    .. code-block:: yaml

      variables:
        file_path: some-file.yml

  .. data:: variables.sys_path
    :type: str | None
    :value: ./

    Directory to use as the root of a relative :data:`variables.file_path`.
    If not provided, the current working directory is used.

    .. rubric:: Example
    .. code-block:: yaml

      variables:
        sys_path: ./../variables


----



**********
Deployment
**********

.. class:: deployment

  A deployment defines modules and options that affect the modules.

  Deployments are processed during a :ref:`commands:deploy`/:ref:`commands:destroy`/:ref:`commands:plan` action.
  If the processing of one deployment fails, the action will end.

  During a :ref:`commands:deploy`/:ref:`commands:destroy` action, the user has the option to select which deployment will run unless the ``CI`` environment variable (``--ci`` cli option) is set, the ``--tag <tag>...`` cli option was provided, or only one deployment is defined.

  .. rubric:: Lookup Support

  .. important::
    Due to how a deployment is processed, some values are resolved twice.
    Once before processing and once during processing.

    Because of this, the fields that are resolved before processing begins will not have access to values set during processing like ``AWS_REGION``, ``AWS_DEFAULT_REGION``, and ``DEPLOY_ENVIRONMENT`` for the pre-processing resolution which can result in a :exc:`FailedLookup` error.
    To avoid errors during the first resolution due to the value not existing, provide a default value for the :ref:`Lookup <Lookups>`.

    The values mentioned will be set before the second resolution when processing begins.
    This ensures that the correct values are passed to the module.

    Impacted fields are marked with an asterisk (*).

  The following fields support lookups:

  - :attr:`~deployment.account_alias` *
  - :attr:`~deployment.account_id` *
  - :attr:`~deployment.assume_role` *
  - :attr:`~deployment.env_vars` *
  - :attr:`~deployment.environments`
  - :attr:`~deployment.module_options`
  - :attr:`~deployment.parallel_regions` *
  - :attr:`~deployment.parameters`
  - :attr:`~deployment.regions` *


  .. attribute:: account_alias
    :type: str | None
    :value: None

    An `AWS account alias <https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html>`__ use to verify the currently assumed role or credentials.
    Verification is performed by listing the account's alias and comparing the result to what is defined.
    This requires the credentials being used to have ``iam:ListAccountAliases`` permissions.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a literal value

      deployments:
        - account_alias: example-dev

    .. code-block:: yaml
      :caption: using a lookup

      deployments:
        - account_alias: example-${env DEPLOY_ENVIRONMENT}
        - account_alias: ${var account_alias.${env DEPLOY_ENVIRONMENT}}

      variables:
        account_alias:
          dev: example-dev

    .. versionchanged:: 2.0.0
      No longer accepts a :class:`typing.Dict`.

  .. attribute:: account_id
    :type: str | None
    :value: None

    An AWS account ID use to verify the currently assumed role or credentials.
    Verification is performed by `getting the caller identity <https://docs.aws.amazon.com/STS/latest/APIReference/API_GetCallerIdentity.html>`__.
    This does not required any added permissions as it is allowed by default.
    However, it does require that ``sts:GetCallerIdentity`` is not explicitly denied.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a literal value

      deployments:
        - account_id: 123456789012

    .. code-block:: yaml
      :caption: using a lookup

      deployments:
        - account_id: ${var account_id.${env DEPLOY_ENVIRONMENT}}

      variables:
        account_id:
          dev: 123456789012

    .. versionchanged:: 2.0.0
      No longer accepts a :class:`typing.Dict`.

  .. attribute:: assume_role
    :type: assume_role_definition | str | None
    :value: {}

    Assume an AWS IAM role when processing the deployment.
    The credentials being used prior to assuming the role must to ``iam:AssumeRole`` permissions for the role provided.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a literal value

      deployments:
        - assume_role: arn:aws:iam::123456789012:role/name

    .. code-block:: yaml
      :caption: using a lookup in a detailed definition

      deployments:
        - assume_role:
            arn: ${var assume_role.${env DEPLOY_ENVIRONMENT}}
            post_deploy_env_revert: True

      variables:
        assume_role:
          dev:
            arn:aws:iam::123456789012:role/name

    .. versionchanged:: 2.0.0
      No longer accepts a :class:`typing.Dict` defining a value per deploy environment.

    .. class:: assume_role_definition

      .. attribute:: arn
        :type: str

        The ARN of the AWS IAM role to be assumed.

      .. attribute:: duration
        :type: int
        :value: 3600

        The duration, in seconds, of the session.

      .. attribute:: post_deploy_env_revert
        :type: bool
        :value: false

        Revert the credentials stored in environment variables to what they were prior to execution after the deployment finished processing.

      .. attribute:: session_name
        :type: str
        :value: runway

        An identifier for the assumed role session.

  .. attribute:: env_vars
    :type: dict[str, list[str] | str] | None
    :value: {}

    Additional variables to add to the environment when processing the deployment.

    Anything defined here is merged with the value of :attr:`module.env_vars`.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - env_vars:
            NAME: value
            KUBECONFIG:
              - .kube
              - ${env DEPLOY_ENVIRONMENT}
              - config

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - env_vars: ${var env_vars.${env DEPLOY_ENVIRONMENT}}

      variables:
        env_vars:
          dev:
            NAME: value

    .. versionchanged:: 2.0.0
      No longer accepts a :class:`typing.Dict` defining a value per deploy environment.
      The entire value of the field is used for all environments.

  .. attribute:: environments
    :type: dict[str, bool | list[str] | str] | None
    :value: {}

    Explicitly enable/disable the deployment for a specific deploy environment, AWS Account ID, and AWS Region combination.
    Can also be set as a static boolean value.

    Anything defined here is merged with the value of :attr:`module.environments`.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - environments:
            dev: True
            test: 123456789012
            qa: us-east-1
            prod:
              - 123456789012/ca-central-1
              - us-west-2
              - 234567890123

    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - environments: ${var environments}

      variables:
        environments:
          dev: True

    .. versionchanged:: 1.4.0
      Now acts as an explicit toggle for deploying modules to a set AWS Account/AWS Region.
      For passing values to a module, :attr:`deployment.parameters`/:attr:`module.parameters` should be used instead.

    .. versionchanged:: 2.0.0
      If defined and the current deploy environment is missing from the definition, processing will be skipped.

  .. attribute:: modules
    :type: list[module | str]

    A list of modules to process as part of a deployment.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
            - sampleapp-01.cfn
            - path: sampleapp-02.cfn

  .. attribute:: module_options
    :type: dict[str, Any] | str | None
    :value: {}

    Options that are passed directly to the modules within this deployment.

    Anything defined here is merged with the value of :attr:`module.options`.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - module_options:
            example: value

    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - module_options:
            example: ${var example}

      variables:
        example: value

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - module_options: ${var parameters}

      variables:
        parameters:
          example: value

  .. attribute:: name
    :type: str | None
    :value: None

    The name of the deployment to be displayed in logs and the interactive selection menu.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - name: networking

  .. attribute:: parallel_regions
    :type: list[str] | str | None
    :value: []

    A list of AWS Regions to process asynchronously.

    Only one of :attr:`~deployment.parallel_regions` or :attr:`~deployment.regions` can be defined.

    Asynchronous deployment only takes effect when running non-interactively.
    Otherwise processing will occur synchronously.

    :attr:`assume_role.post_deploy_env_revert <assume_role_definition.post_deploy_env_revert>` will always be ``true`` when run in parallel.

    Can be used in tandem with :attr:`module.parallel`.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - parallel_regions:
            - us-east-1
            - us-west-2
            - ${var third_region.${env DEPLOY_ENVIRONMENT}}

      variables:
        third_region:
          dev: ca-central-1

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
          - parallel_regions: ${var regions.${env DEPLOY_ENVIRONMENT}}

        variables:
          regions:
            - us-east-1
            - us-west-2

    .. versionadded:: 1.3.0

  .. attribute:: parameters
    :type: dict[str, Any] | str | None
    :value: {}

    Used to pass variable values to modules in place of an environment configuration file.

    Anything defined here is merged with the value of :attr:`module.parameters`.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - parameters:
            namespace: example-${env DEPLOY_ENVIRONMENT}

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - parameters: ${var parameters.${env DEPLOY_ENVIRONMENT}}

      variables:
        parameters:
          dev:
            namespace: example-dev

    .. versionadded:: 1.4.0

  .. attribute:: regions
    :type: dict[str, list[str] | str] | list[str] | str | None
    :value: []

    A list of AWS Regions to process this deployment in.

    Only one of :attr:`~deployment.parallel_regions` or :attr:`~deployment.regions` can be defined.

    Can be used to define asynchronous processing similar to :attr:`~deployment.parallel_regions`.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: synchronous

      deployments:
        - regions:
            - us-east-1
            - us-west-2

    .. code-block:: yaml
      :caption: asynchronous

      deployments:
        - regions:
            parallel:
              - us-east-1
              - us-west-2
              - ${var third_region.${env DEPLOY_ENVIRONMENT}}

      variables:
        third_region:
          dev: ca-central-1

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
          - regions: ${var regions.${env DEPLOY_ENVIRONMENT}}

        variables:
          regions:
            - us-east-1
            - us-west-2

    .. versionchanged 1.3.0
      Added support for asynchronous processing.


----



******
Module
******

.. class:: module

  A :term:`Module` defines the directory to be processed and applicable options.

  It can consist of :ref:`index:CloudFormation & Troposphere`, :ref:`index:Terraform`, :ref:`index:Serverless Framework`, :ref:`index:AWS Cloud Development Kit (CDK)`, :ref:`index:Kubernetes`, or a :ref:`index:Static Site`.
  It is recommended to place the appropriate extension on each directory for identification (but it is not required).
  See :ref:`repo_structure:Repo Structure` for examples of a module directory structure.

  +------------------+---------------------------------------------------------+
  | Suffix/Extension | IaC Tool/Framework                                      |
  +==================+=========================================================+
  | ``.cdk``         | :ref:`index:AWS Cloud Development Kit (CDK)`            |
  +------------------+---------------------------------------------------------+
  | ``.cfn``         | :ref:`index:CloudFormation & Troposphere`               |
  +------------------+---------------------------------------------------------+
  | ``.k8s``         | :ref:`index:Kubernetes`                                 |
  +------------------+---------------------------------------------------------+
  | ``.sls``         | :ref:`index:Serverless Framework`                       |
  +------------------+---------------------------------------------------------+
  | ``.tf``          | :ref:`index:Terraform`                                  |
  +------------------+---------------------------------------------------------+
  | ``.web``         | :ref:`index:Static Site`                                |
  +------------------+---------------------------------------------------------+

  A module is only deployed if there is a corresponding environment file present, it is explicitly enabled via :attr:`deployment.environments`/:attr:`module.environments`, or :attr:`deployment.parameters`/:attr:`module.parameters` is defined.
  The naming format of an environment file varies per module type.
  See :ref:`index:Module Configuration` for acceptable environment file name formats.

  Modules can be defined as a string or a mapping.
  The minimum requirement for a module is a string that is equal to the name of the module directory.
  Providing a string is the same as providing a value for :attr:`~module.path` in a mapping definition.

  Using a mapping to define a module provides the ability to specify all the fields listed here.

  .. rubric:: Lookup Support

  The following fields support lookups:

  - :attr:`~module.class_path`
  - :attr:`~module.env_vars`
  - :attr:`~module.environments`
  - :attr:`~module.options`
  - :attr:`~module.parameters`
  - :attr:`~module.path`

  .. attribute:: class_path
    :type: str | None
    :value: null

    .. note::
      Most users will never need to use this.
      It is only used for custom module type handlers.

    Import path to a custom Runway module handler class.
    See :ref:`index:Module Configuration` for detailed usage.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - class_path: runway.module.cloudformation.CloudFormation

  .. attribute:: env_vars
    :type: dict[str, list[str] | str] | None
    :value: {}

    Additional variables to add to the environment when processing the deployment.

    Anything defined here is merged with the value of :attr:`deployment.env_vars`.
    Values defined here take precedence.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - modules:
          - env_vars:
              NAME: VALUE
              KUBECONFIG:
                - .kube
                - ${env DEPLOY_ENVIRONMENT}
                - config

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - modules:
            - env_vars: ${var env_vars.${env DEPLOY_ENVIRONMENT}}

      variables:
        env_vars:
          dev:
            NAME: value

    .. versionchanged:: 2.0.0
      No longer accepts a :class:`typing.Dict` defining a value per deploy environment.
      The entire value of the field is used for all environments.

  .. attribute:: environments
    :type: dict[str, bool | list[str] | str] | None
    :value: {}

    Explicitly enable/disable the deployment for a specific deploy environment, AWS Account ID, and AWS Region combination.
    Can also be set as a static boolean value.

    Anything defined here is merged with the value of :attr:`deployment.environments`.
    Values defined here take precedence.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - environments:
            dev: True
            test: 123456789012
            qa: us-east-1
            prod:
              - 123456789012/ca-central-1
              - us-west-2
              - 234567890123

    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - modules:
          - environments: ${var environments}

      variables:
        environments:
          dev: True

    .. versionchanged:: 1.4.0
      Now acts as an explicit toggle for deploying modules to a set AWS Account/AWS Region.
      For passing values to a module, :attr:`deployment.parameters`/:attr:`module.parameters` should be used instead.

    .. versionchanged:: 2.0.0
      If defined and the current deploy environment is missing from the definition, processing will be skipped.

  .. attribute:: name
    :type: str | None

    The name of the module to be displayed in logs and the interactive selection menu.

    If a name is not provided, the :attr:`~module.path` value is used.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - name: networking

  .. attribute:: options
    :type: dict[str, Any] | str | None
    :value: {}

    Options that are passed directly to the module type handler class.

    The options that can be used with each module vary.
    For detailed information about options for each type of module, see :ref:`index:Module Configuration`.

    Anything defined here is merged with the value of :attr:`deployment.module_options`.
    Values defined here take precedence.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - module:
          - options:
              example: value

    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - module:
          - options:
              example: ${var example}

      variables:
        example: value

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - module:
          - options: ${var parameters}

      variables:
        parameters:
          example: value

  .. attribute:: parallel
    :type: list[module] | None
    :value: []

    List of `module` definitions that can be executed asynchronously.

    Incompatible with :attr:`~module.class_path`, :attr:`~module.path`, and :attr:`~module.type`.

    Asynchronous deployment only takes effect when running non-interactively.
    Otherwise processing will occur synchronously.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - parallel:
            - path: sampleapp-01.cfn
            - path: sampleapp-02.cfn

  .. attribute:: parameters
    :type: dict[str, Any] | str | None
    :value: {}

    Used to pass variable values to modules in place of an environment configuration file.

    Anything defined here is merged with the value of :attr:`deployment.parameters`.
    Values defined here take precedence.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup as the value

      deployments:
        - modules:
          - parameters:
              namespace: example-${env DEPLOY_ENVIRONMENT}

    .. code-block:: yaml
      :caption: using a lookup in the value

      deployments:
        - modules:
          - parameters: ${var parameters.${env DEPLOY_ENVIRONMENT}}

      variables:
        parameters:
          dev:
            namespace: example-dev

    .. versionadded:: 1.4.0

  .. attribute:: path
    :type: str | Path | None

    Directory (relative to the Runway config file) containing IaC.
    The directory can either be on the local file system or a network accessible location.

    See path_ for more detailed information.

    .. rubric:: Example
    .. code-block:: yaml
      :caption: using a lookup

      deployments:
        - modules:
          - path: sampleapp-${env DEPLOY_ENVIRONMENT}.cfn

    .. versionadded:: 1.4.0

  .. attribute:: tags
    :type: list[str] | None
    :value: []

    A list of strings to categorize the module which can be used with the CLI to quickly select a group of modules.

    This field is only used by the ``--tag`` CLI option.

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - tags:
            - app:sampleapp
            - type:network

  .. attribute:: type
    :type: str | None

    Explicitly define the type of IaC contained within the directory.
    This can be useful when Runway fails to automatically determine the correct module type.

    .. rubric:: Accepted Values

    - cdk
    - cloudformation
    - kubernetes
    - serverless
    - terraform
    - static

    .. rubric:: Example
    .. code-block:: yaml

      deployments:
        - modules:
          - type: static

    .. versionadded:: 1.4.0



path
====

:attr:`~module.path` can either be defined as a local path relative to the Runway config file or a network accessible (remote) location.

When the value is identified as a remote location, Runway is responsible for retrieving resources from the location and caching them locally for processing.
This allows the remote resources to be handled automatically by Runway rather than needing to manually retrieve them or employ another mechanism to retrieve them.

Remote Location Syntax
----------------------

The syntax is based on that of `Terraform module sources <https://www.terraform.io/docs/modules/sources.html>`__.

.. code-block:: shell

  ${source}::${uri}//${location}?${arguments}

:source:
  Combined with the following ``::`` separator, it is used to identify the location as remote.
  The value determines how Runway with handle retrieving resources from the remote location.

:uri:
  The uniform resource identifier when targeting a remote resource.
  This instructs runway on where to retrieve your module.

:location:
  An optional location within the remote location (assessed after the resources have been retrieve) relative to the root of the retrieve resources.

  This field is preceded by a ``//``. If not defining a location, this separator does not need to be provided.

:arguments:
  An optional ampersand (``&``) delimited list of ``key=value`` pairs that are unique to each remote location source.
  These are used to provide granular control over how Runway retrieves resources from the remote location.

  This field is preceded by a ``?``. If not defining a location, this separator does not need to be provided.


Remote Location Sources
-----------------------


Git Repository
^^^^^^^^^^^^^^

Runway can retrieve a git repository to process modules contained within it.
Below is an example of using a module in a git repository as well as a breakdown of the values being provided to each field.

.. code-block:: yaml

  deployments:
      - modules:
          # ${source}::${uri}//${location}?${arguments}
          - path: git::git://github.com/foo/bar.git//my/path?branch=develop

+-----------+----------------------------------+------------------------------------------------------+
| Field     | Value                            | Description                                          |
+===========+==================================+======================================================+
| source    | ``git``                          | The *type* of remote location source.                |
+-----------+----------------------------------+------------------------------------------------------+
| uri       | ``git://github.com/foo/bar.git`` | The protocol and URI address of the git repository.  |
+-----------+----------------------------------+------------------------------------------------------+
| location  | ``my/path``                      | | The relative path from the root of the repo where  |
|           |                                  | | the module is located. *(optional)*                |
+-----------+----------------------------------+------------------------------------------------------+
| arguments | ``branch=develop``               | | After cloning the repository, checkout the develop |
|           |                                  | | branch. *(optional)*                               |
+-----------+----------------------------------+------------------------------------------------------+

.. rubric:: Arguments

:branch:
  Name of a branch to checkout after cloning the git repository.

  Only one of *branch*, *commit*, or *tag* can be defined.
  If none are defined, *HEAD* is used.

:commit:
  After cloning the git repository, reset *HEAD* to the given commit hash.

  Only one of *branch*, *commit*, or *tag* can be defined.
  If none are defined, *HEAD* is used.

:tag:
  After cloning the git repository, reset *HEAD* to the given tag.

  Only one of *branch*, *commit*, or *tag* can be defined.
  If none are defined, *HEAD* is used.
