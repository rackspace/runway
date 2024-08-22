.. _cfngin-configuration:

#############
Configuration
#############

In addition to the :ref:`runway_config:Runway Config File`, there are two files that can be used for configuration:

- a YAML :ref:`configuration file <cfngin-config>` **[REQUIRED]**
- a key/value :ref:`environment file <cfngin-env>`


.. versionchanged:: 1.5.0
  Stacker is no longer used for handling CloudFormation/Troposphere.
  It has been replaced with an internal CloudFormation engin (CFNgin).



**********
runway.yml
**********

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.cfn
          type: cloudformation  # not required; implied from ".cfn" directory extension
          environments:
            dev: true
          parameters:
            namespace: example-${env DEPLOY_ENVIRONMENT}
            cfngin_bucket: example-${env DEPLOY_ENVIRONMENT}-${env AWS_REGION}
      regions:
        - us-east-1


Options
=======

CloudFormation modules do not have any module-specific options.


Parameters
==========

Runway can pass :term:`Parameters` to a CloudFormation module in place of or in addition to values in an :ref:`environment file <cfngin-env>`.
When :term:`Parameters` are passed to the module, the data type is retained (e.g. ``array``, ``boolean``, ``mapping``).

A typical usage pattern would be to use :ref:`Runway Lookups <Lookups>` in combination with :term:`Parameters` to pass :term:`Deploy Environment` and/or region specific values to the module from the :ref:`runway_config:Runway Config File`.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - sampleapp-01.cfn
        - path: sampleapp-02.cfn
          parameters:
            instance_count: ${var instance_count.${env DEPLOY_ENVIRONMENT}}
      parameters:
        image_id: ${var image_id.%{env AWS_REGION}}

Common Parameters
-----------------

Runway automatically makes the following commonly used :term:`Parameters`  available to CloudFormation modules.

.. note::
  If these parameters are already being explicitly defined in :attr:`deployment.parameters`/:attr:`module.parameters` the value provided will be used instead of what would be automatically added.

.. data:: environment
  :type: str
  :noindex:

  Taken from the ``DEPLOY_ENVIRONMENT`` environment variable. This will the be current :term:`Deploy Environment`.

.. data:: region
  :type: str
  :noindex:

  Taken from the ``AWS_REGION`` environment variable. This will be the current region being processed.



----


.. _cfngin-config:

******************
CFNgin Config File
******************

The CFNgin config file has full support for YAML features like `anchors & references <https://en.wikipedia.org/wiki/YAML#Advanced_components>`_ for a DRY config file (See :ref:`YAML anchors & references <cfngin-yaml>` for details).


Top-Level Fields
================

.. class:: cfngin.config

  Runway's CFNgin makes use of a YAML formatted config file to define the different CloudFormation stacks that make up a given environment.

  .. _cfngin-bucket:

  .. attribute:: cfngin_bucket
    :type: str | None
    :value: None

    By default, CloudFormation templates are pushed into an S3 bucket and CloudFormation is pointed to the template in that bucket when launching or updating stacks.
    By default it uses a bucket named ``cfngin-${namespace}-${region}``, where the namespace is :attr:`~cfngin.config.namespace` and region is the current AWS region.

    To change this, define a value for this field.

    If the bucket does not exists, CFNgin will try to create it in the same region that the stacks will be launched in.
    The bucket will be created by deploying a CloudFormation stack named ``${namespace}-cfngin-bucket`` where the namespace is :attr:`~cfngin.config.namespace`.
    If there is a stack named ``cfngin-bucket`` found defined in the :attr:`~cfngin.config.stacks` field, it will be used in place of default :class:`~cfngin.stack` & Blueprint (:class:`runway.cfngin.blueprints.cfngin_bucket.CfnginBucket`) provided by CFNgin.
    When using a custom stack, it is the user's responsibility to ensure that a bucket with the correct name is created by this stack.

    If you want CFNgin to upload templates directly to CloudFormation instead of first uploading to S3, you can set this field to an empty string.
    However, the template size is greatly limited when uploading directly.
    See the `CloudFormation Limits Reference <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cloudformation-limits.html>`__.

    .. tip::
      Defining a :class:`~cfngin.stack` that uses the Blueprint provided by CFNgin allows for easy customization of stack fields such as :attr:`~cfngin.stack.tags`.
      It also allows the stack to be deleted as part of the normal deletion process.
      If it is not defined as a stack, CFNgin won't delete the stack or bucket.

      .. code-block:: yaml

        namespace: ${namespace}
        cfngin_bucket: cfngin-${namespace}-${region}

        stacks:
          - name: cfngin-bucket
            class_path: runway.cfngin.blueprints.cfngin_bucket.CfnginBucket
            variables:
              BucketName: cfngin-${namespace}-${region}

        pre_destroy:
          - path: runway.cfngin.hooks.cleanup_s3.purge_bucket
            args:
              bucket_name: cfngin-${namespace}-${region}

    .. rubric:: Example
    .. code-block:: yaml

        cfngin_bucket: example-${region}

    .. code-block: yaml
      :caption: disable caching

        cfngin_bucket: ""

    .. versionchanged:: 2.0.0
      The format of the default value is now ``cfngin-${namespace}-${region}``.

  .. attribute:: cfngin_bucket_region
    :type: str | None
    :value: None

    AWS Region where :attr:`~cfngin.config.cfngin_bucket` is located.
    This can be different than the region currently being deployed to but, ensure to account for all AWS limitations before manually setting this value.

    If not provided, the current region is used.

    .. rubric:: Example
    .. code-block:: yaml

        cfngin_bucket_region: us-east-1

  .. attribute:: cfngin_cache_dir
    :type: str | None
    :value: ./.runway/

    Path to a local directory that CFNgin will use for local caching.

    If provided, the cache location is relative to the CFNgin configuration file.

    If NOT provided, the cache location is relative to the ``runway.yaml``/``runway.yml`` file and is shared between all Runway modules.

    .. rubric:: Example
    .. code-block:: yaml

        cfngin_cache_dir: ./.runway

  .. attribute:: log_formats
    :type: dict[str, str]
    :value: {}

    Customize log message formatting by log level.

    Any of the standard Python `logging module format attributes <https://docs.python.org/2.7/library/logging.html#logrecord-attributes>`__ can be used when writing a new log format string.

    .. rubric:: Example
    .. code-block:: yaml

      log_formats:
        info: "[%(asctime)s] %(message)s"
        debug: "[%(asctime)s] %(levelname)s %(threadName)s %(name)s:%(lineno)d(%(funcName)s): %(message)s"

  .. attribute:: lookups
    :type: dict[str, str]
    :value: {}

    Lookups allow you to create custom methods which take a value and are resolved at runtime time.
    The resolved values are passed to the |Blueprint| before it is rendered.
    For more information, see the :ref:`Lookups <cfngin-lookups>` documentation.

    CFNgin provides some common :ref:`Lookups <cfngin-lookups>`, but it is sometimes useful to have your own custom lookup that doesn't get shipped with Runway.
    You can register your own lookups here.

    The *key* of each item in the mapping will be used as the name of the lookup type when registering the lookup.
    The *value* should be the path to a valid lookup handler.

    .. rubric:: Example
    .. code-block:: yaml

      lookups:
        custom: path.to.lookup.handler

      conf_value: ${custom query}

  .. attribute:: mappings
    :type: dict[str, dict[str, dict[str, Any]]]
    :value: {}

    Mappings are dictionaries that are provided as `Mappings <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/mappings-section-structure.html>`__ to each CloudFormation stack that CFNgin produces.

    These can be useful for providing things like different AMIs for different instance types in different regions.

    These can be used in each |Blueprint|/template as usual.

    .. rubric:: Example
    .. code-block:: yaml

      mappings:
        AmiMap:
          us-east-1:
            NAT: ami-ad227cc4
            ubuntu1404: ami-74e27e1c
            bastion: ami-74e27e1c
          us-west-2:
            NAT: ami-290f4119
            ubuntu1404: ami-5189a661
            bastion: ami-5189a661

  .. attribute:: namespace
    :type: str

    A *namespace* to create all stacks within.
    The value will be used as a prefix for the name of any stack that is created.

    In addition, this value can be used to create an S3 bucket that will be used to upload and store all CloudFormation templates.
    See :attr:`~cfngin.config.cfngin_bucket` for more detailed information.

    In general, this is paired with the concept of :term:`Deploy Environments <Deploy Environment>` to create a namespace per environment.

    .. rubric:: Example
    .. code-block:: yaml

      namespace: ${namespace}-${environment}

  .. attribute:: namespace_delimiter
    :type: str | None
    :value: "-"

    By default, ``-`` will be used as a delimiter between the :attr:`~cfngin.config.namespace` and the declared stack name to deploy the actual CloudFormation stack name that gets created.

    If you prefer to not use a delimiter, an empty string can be used as the value of this field.

    See the `CloudFormation API Reference <http://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStack.html>`__ for allowed stack name characters

    .. rubric:: Example
    .. code-block:: yaml

      namespace_delimiter: ""

  .. attribute:: package_sources
    :type: cfngin.package_sources
    :value: {}

    See :ref:`Remote Sources <cfngin_remote_sources>` for detailed information.

    .. rubric: Example
    .. code-block:: yaml

      package_sources:
        git:
          ...
        local:
          ...
        s3:
          ...

  .. attribute:: persistent_graph_key
    :type: str | None
    :value: None

    Used to track the *state* of stacks defined in configuration file.
    This can result in stacks being destroyed when they are removed from the configuration file removing the need to manually delete the stacks.

    See :ref:`Persistent Graph <cfngin_persistent_graph>` for detailed information.

    .. rubric:: Example
    .. code-block:: yaml

      persistent_graph_key: unique-key.json

  .. attribute:: post_deploy
    :type: list[cfngin.hook]
    :value: []

    Python functions/methods that are executed after processing the stacks in the config while using the :ref:`commands:deploy` command.

    See :ref:`Hooks <cfngin-hooks>` for more detailed information.

    .. rubric:: Example
    .. code-block:: yaml

      post_deploy:
        - path: do.something

    .. versionchanged:: 2.0.0
      *post_build* renamed to *post_deploy*.

    .. versionchanged:: 2.2.0
      The CFNgin bucket is now created using a CloudFormation stack.

  .. attribute:: post_destroy
    :type: list[cfngin.hook]
    :value: []

    Python functions/methods that are executed after processing the stacks in the config while using the :ref:`commands:destroy` command.

    See :ref:`Hooks <cfngin-hooks>` for more detailed information.

    .. rubric:: Example
    .. code-block:: yaml

      post_destroy:
        - path: do.something

  .. attribute:: pre_deploy
    :type: list[cfngin.hook]
    :value: []

    Python functions/methods that are executed before processing the stacks in the config while using the :ref:`commands:deploy` command.

    See :ref:`Hooks <cfngin-hooks>` for more detailed information.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - path: do.something

    .. versionchanged:: 2.0.0
      *pre_build* renamed to *pre_deploy*.

  .. attribute:: pre_destroy
    :type: list[cfngin.hook]
    :value: []

    Python functions/methods that are executed before processing the stacks in the config while using the :ref:`commands:destroy` command.

    See :ref:`Hooks <cfngin-hooks>` for more detailed information.

    .. rubric:: Example
    .. code-block:: yaml

      pre_destroy:
        - path: do.something

  .. attribute:: service_role
    :type: str | None
    :value: None

    By default CFNgin doesn't specify a service role when executing changes to CloudFormation stacks.
    If you would prefer that it do so, you define the IAM Role ARN that CFNgin should use when executing CloudFormation changes.

    This is the equivalent of setting ``RoleARN`` on a call to the following CloudFormation API calls: ``CreateStack``, ``UpdateStack``, ``CreateChangeSet``.

    See the `AWS CloudFormation service role <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html?icmpid=docs_cfn_console>`__ for more information.

    .. rubric:: Example
    .. code-block:: yaml

      service_role: arn:aws:iam::123456789012:role/name

  .. attribute:: stacks
    :type: list[cfngin.stack]
    :Value: []

    This is the core part of the config where the CloudFormations stacks that will be deployed in the environment are defined.

    See Stack_ for more information.

  .. attribute:: sys_path
    :type: str | None
    :value: None

    A path to be added to ``$PATH`` while processing the configuration file.
    This will allow modules from the provided path location to be used.

    When setting :attr:`~cfngin.stack.class_path` for a |Blueprint| or :attr:`~cfngin.hook.path` for a :class:`hook <cfngin.hook>` , it is sometimes desirable to load modules from outside the default ``$PATH`` (e.g. to include modules inside the same repo as config files).

    .. rubric:: Example
    .. code-block:: yaml

      sys_path: ./  # most common value to use

  .. attribute:: tags
    :type: dict[str, str]
    :value: {"cfngin_namespace": namespace}

    A dictionary of tags to add to all stacks.
    These tags are propagated to all resources that AWS CloudFormation supports.
    See `CloudFormation - Resource Tag`_ for more information.

    If this field is undefined, a **cfngin_namespace** tag is applied to your stack with the value of :attr:`~cfngin.config.namespace` as the tag-value.
    Alternatively, this field can be set to a value of ``{}`` (an empty dictionary) to disable the default tag.

    .. _`CloudFormation - Resource Tag`: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-resource-tags.html

    .. rubric:: Example
    .. code-block:: yaml

      tags:
        namespace: ${namespace}
        example: value

    .. code-block:: yaml
      :caption: disable default tag

      tags: {}

  .. attribute:: template_indent
    :type: int | None
    :value: 4

    Number of spaces per indentation level to use when rendering/outputting CloudFormation templates.

    .. rubric:: Example
    .. code-block:: yaml

      template_indent: 2


Stack
=====

.. class:: cfngin.stack

  Defines a CloudFormation stack.

  .. rubric:: Lookup Support

  The following fields support lookups:

  - :attr:`~cfngin.stack.variables`

  .. rubric:: Example
  .. code-block:: yaml

    stacks:
      - name: vpc-example
        class_path: blueprints.vpc.VPC
        variables:
          InstanceType: t2.small
          SshKeyName: default
          ImageName: NAT
          AZCount: 2
          PublicSubnets:
            - 10.128.0.0/24
            - 10.128.1.0/24
            - 10.128.2.0/24
            - 10.128.3.0/24
          PrivateSubnets:
            - 10.128.8.0/22
            - 10.128.12.0/22
            - 10.128.16.0/22
            - 10.128.20.0/22
          CidrBlock: 10.128.0.0/16

  .. attribute:: class_path
    :type: str | None
    :value: None

    A python importable path to the |Blueprint| class to be used.

    Exactly one of :attr:`~cfngin.stack.class_path` or :attr:`~cfngin.stack.template_path` must be defined.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          class_path: example.BlueprintClass

  .. attribute:: description
    :type: str | None
    :value: None

    A short description to apply to the stack.
    This overwrites any description defined in the |Blueprint|.
    See `Cloudformation - Template Description <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-description-structure.html>`__ for more information.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          description: An Example Stack

  .. attribute:: enabled
    :type: bool
    :value: True

    Whether to deploy/update the stack.
    This enables the ability to disable stacks in different environments.

    .. important:: This field is ignored when destroying stacks.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          enabled: false
        - name: another-stack
          enabled: ${enable_another_stack}

  .. attribute:: in_progress_behavior
    :type: Literal["wait"] | None
    :value: None

    Specifies the behavior for when a stack is in ``CREATE_IN_PROGRESS`` or ``UPDATE_IN_PROGRESS``.
    By default, CFNgin will raise an exception if the stack is in an ``IN_PROGRESS`` state when processing begins.

    If the value of this field is *wait*, CFNgin will wait for the previous update to complete before attempting to update the stack instead of raising an exception.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          in_progress_behavior: wait

  .. attribute:: locked
    :type: bool
    :value: False

    Whether the stack should be updated after initial deployment.
    This is useful for *risky* stacks that you don't want to take the risk of allowing CloudFormation to update but still want to deploy it using CFNgin.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          locked: true
        - name: another-stack
          locked: ${locked_another_stack}

  .. attribute:: name
    :type: str

    Name of the CFNgin Stack.
    The value of this field is used by CFNgin when referring to a Stack.
    It will also be used as the name of the Stack when created in CloudFormation unless overridden by :attr:`~stack.stack_name`.

    .. note::
      :attr:`~cfngin.config.namespace` will be appended to this value when used as the name of the CloudFormation Stack.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack

  .. attribute:: protected
    :type: bool
    :value: False

    Whether to force all updates to be performed interactively.

    When true and running in non-interactive mode, CFNgin will switch to interactive mode for this stack to require manual review and approval of any changes.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          protected: true
        - name: another-stack
          protected: ${protected_another_stack}

  .. attribute:: required_by
    :type: list[str]
    :value: []

    A list of other stacks that require this stack.
    All stacks must be defined in the same configuration file.

    Inverse of :attr:`~cfngin.stack.requires`.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack:  # deployed first
          required_by:
            - another-stack
        - name: another-stack:  # deployed after example-stack
          ...

  .. attribute:: requires
    :type: list[str]
    :value: []

    A list of other stacks that this stack requires.
    All stacks must be defined in the same configuration file.

    Inverse of :attr:`~cfngin.stack.required_by`.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack# deployed after another-stack
          requires:
            - another-stack
        - name: another-stack  # deployed first
          ...

  .. attribute:: stack_name
    :type: str | None
    :value: None

    The name used when creating the CloudFormation stack.
    If not provided, :attr:`~stack.name` will be used.

    .. note:: :attr:`~cfngin.config.namespace` will be appended to this value.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          stack_name: another-name

  .. attribute:: stack_policy_path
    :type: str | None
    :value: None

    Path to a JSON formatted stack policy that will be applied when the CloudFormation stack is created and/or updated.

    See `CloudFormation - Prevent updates to stack resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html>`__ for examples and more information.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          stack_policy_path: ./stack_policies/example-stack.json

  .. attribute:: tags
    :type: dict[str, str]
    :value: {}

    A dictionary of tags to add to the Stack.
    These tags are propagated to all resources that AWS CloudFormation supports.
    See `CloudFormation - Resource Tag`_ for more information.

    This will be combined with the global :attr:`~cfngin.config.tags`.
    Values defined here take precedence over those defined globally.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          tags:
            namespace: ${namespace}
            example: value

  .. attribute:: template_path
    :type: str | None

    Path to a raw CloudFormation template (JSON or YAML).
    Can be relative to the working directory (e.g. templates stored alongside the configuration file), or relative to a directory in the *$PATH* (i.e. for loading templates retrieved via :attr:`~cfngin.config.package_sources`).

    Exactly one of :attr:`~cfngin.stack.class_path` or :attr:`~cfngin.stack.template_path` must be provided.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          template_path: ./templates/example-stack.yml
        - name: another-stack
          template_path: remote/path/templates/another-stack.json

  .. attribute:: termination_protection
    :type: bool
    :value: False

    Whether the stack will be protected from termination by CloudFormation.

    Any attempts to destroy the stack (using Runway, the AWS console, AWS API, etc) will be prevented unless manually disabled.

    When updating a stack and the value has been changed, termination protection on the CloudFormation stack sill also change.
    This is useful when needing to destroy a stack by first changing the value in the configuration file, updating the stack, then proceeding to destroy it.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          termination_protection: true
        - name: another-stack
          termination_protection: ${termination_protection_another_stack}

  .. attribute:: timeout
    :type: int | None
    :value: None

    Specifies the amount of time, in minutes, that CloudFormation should allot before timing out stack creation operations.
    If CloudFormation can't create the entire stack in the time allotted, it fails the stack creation due to timeout and rolls back the stack.

    By default, there is no timeout for stack creation.
    However, individual resources may have their own timeouts based on the nature of the service they implement.
    For example, if an individual resource in your stack times out, stack creation also times out even if the timeout you specified for stack creation hasn't yet been reached.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          timeout: 120

  .. attribute:: variables
    :type: dict[str, Any]
    :value: {}

    A dictionary of Variables_ to pass to the |Blueprint| when rendering the CloudFormation template.
    Can be any valid YAML data structure.

    When using a raw CloudFormation template, these are the values provided for it's *Parameters*.

    .. rubric:: Example
    .. code-block:: yaml

      stacks:
        - name: example-stack
          variables:
            StackVariable: value


.. _cfngin-variables:

Variables
==========

Variables are values that will be passed into a |Blueprint| before it is rendered.
Variables can be any valid YAML data structure and can leverage :ref:`Lookups <cfngin-lookups>` to expand values at runtime.

.. _cfngin-yaml:

YAML anchors & references
-------------------------

If you have a common set of variables that you need to pass around in many places, it can be annoying to have to copy and paste them in multiple places.
Instead, using a feature of YAML known as `anchors & references`_, you can define common values in a single place and then refer to them with a simple syntax.

For example, say you pass a common domain name to each of your stacks, each of them taking it as a Variable.
Rather than having to enter the domain into each stack you could do the following to have an anchor called **domain** that you can use in place of any value in the config to provide the value **mydomain.com**.

.. code-block:: yaml

  stacks:
  - name: example-stack
    class_path: blueprints.Example
    variables:
      DomainName: &domain mydomain.com
    - name: vpc
      class_path: blueprints.VPC
      variables:
        DomainName: *domain

Even more powerful is the ability to anchor entire dictionaries, and then reference them in another dictionary, effectively providing it with default values. Now, rather than having to provide each of those variables to every stack that could use them, you can just do this instead.

.. code-block:: yaml

  stacks:
    - name: example-stack
      class_path: blueprints.Example
      variables: &variables
        DomainName: mydomain.com
        InstanceType: m3.medium
        AMI: ami-12345abc
    - name: vpc
      class_path: blueprints.VPC
      variables:
        << : *variables
        InstanceType: c4.xlarge # override the InstanceType in this stack


Using Outputs as Variables
---------------------------

Since CFNgin encourages the breaking up of your CloudFormation stacks into entirely separate stacks, sometimes you'll need to pass values from one stack to another.
The way this is handled in CFNgin is by having one stack provide :term:`Outputs <Output>` for all the values that another stack may need, and then using those as the inputs for another stack's :attr:`~cfngin.stack.variables`.
CFNgin makes this easier for you by providing a syntax for :attr:`~cfngin.stack.variables` that will cause CFNgin to automatically look up the values of :term:`Outputs <Output>` from another stack in its config.

To do so, use the :ref:`output lookup` in the :attr:`~cfngin.stack.variables` on the target stack.

.. code-block:: yaml

  MyParameter: ${output OtherStack.OutputName}

For more information see :ref:`Lookups <cfngin-lookups>`.

In this example config, when deploying things inside a VPC, you will need to pass the **VpcId** of the VPC that you want the resources to be located in.
If the **vpc** stack provides an Output called **VpcId**, you can reference it easily.

.. code-block:: yaml

  domain_name: my_domain &domain

  stacks:
    - name: vpc
      class_path: blueprints.vpc.VPC
      variables:
        DomainName: *domain
    - name: webservers
      class_path: blueprints.asg.AutoscalingGroup
      variables:
        DomainName: *domain
        VpcId: ${output vpc.VpcId} # gets the VpcId Output from the vpc stack

Doing this creates an implicit dependency from the **webservers** stack to the **vpc** stack, which will cause CFNgin to submit the **vpc** stack, and then wait until it is complete until it submits the **webservers** stack.
This would be the same as adding **vpc** to the :attr:`~cfngin.stack.requires` field of the **webservers** stack.


----


.. _cfngin-env:

****************
Environment File
****************

When using CFNgin, you can optionally provide an "environment" file.
The CFNgin config file will be interpolated as a `string.Template <https://docs.python.org/2/library/string.html#template-strings>`_ using the key-value pairs from the environment file as :attr:`~module.parameters`.
The format of the file is a single key-value per line, separated by a colon (**:**).


File Naming
===========

Environment files must follow a specific naming format in order to be recognized by Runway.
The files must also be stored at the root of the module's directory.

:${DEPLOY_ENVIRONMENT}-${AWS_REGION}.env:
  The typical naming format that will be used for these files specifies the name of the ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` in which to use the file.

:${DEPLOY_ENVIRONMENT}.env:
  The region can optionally be omitted to apply a single file to all regions.

Files following both naming schemes may be used. The file with the most specific name takes precedence.
Values passed in as ``parameters`` from the :ref:`runway_config:Runway Config File` take precedence over those provided in an environment file.


Usage
=====

A pretty common use case is to have separate environments that you want to look mostly the same, though with some slight modifications.
For example, you might want a **production** and a **staging** environment.

The production environment likely needs more instances, and often those instances will be of a larger instance type.
The parameters defined in an environment file, :attr:`deployment.parameters`, and/or :attr:`module.parameters` allow you to use your existing CFNgin config, but provide different values based on the current :term:`Deploy Environment`.

.. rubric:: Example
.. code-block:: yaml

  vpcID: vpc-12345678

Provided the key-value pair above, you will now be able to use this in your configs for a :term:`Deploy Environment`.
They act as keys that can be used in your config file, providing a sort of templating ability.
This allows you to change the values of your config based on the current :term:`Deploy Environment`.

For example, if you have a **webserver** stack, and you need to provide it a variable for the instance size it should use, you would have something like this in your config file.

.. code-block:: yaml

  stacks:
    - name: webservers
      class_path: blueprints.asg.AutoscalingGroup
      variables:
        InstanceType: m3.medium

But what if you needed more CPU in your production environment, but not in your staging?
Without parameters, you'd need a separate config for each.
With parameters, you can simply define two different values for **InstanceType** in an an environment file, :attr:`deployment.parameters`, and/or :attr:`module.parameters` then use the parameter's name to reference the value in a config file.

.. code-block:: yaml
  :caption: sampleapp.cfn/cfngin.yml

  # in your config file:
  stacks:
    - name: webservers:
      class_path: blueprints.asg.AutoscalingGroup
      variables:
        InstanceType: ${web_instance_type}

.. rubric:: Using Environment Files

Both files would be required.

.. code-block:: yaml
  :caption: sampleapp.cfn/stage.env

  web_instance_type: m5.medium

.. code-block:: yaml
  :caption: sampleapp.cfn/prod.env

  web_instance_type: c5.xlarge

.. rubric:: Using Runway

This option would not required the use of environment files to define the values.

.. code-block:: yaml
  :caption: runway.yaml

  deployments:
    - modules:
      - name: Sample Application
        path: sampleapp.cfn
        parameters:
          web_instance_type: ${var web_instance_type.${env DEPLOY_ENVIRONMENT}}

  variables:
    web_instance_type:
      stage: m5.medium
      prod: c5.xlarge
