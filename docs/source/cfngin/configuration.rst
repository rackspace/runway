.. _Runway Config File: runway_config.html

#############
Configuration
#############

In addition to the `Runway Config File`_, there are two files that can be used for configuration:

- a YAML :ref:`configuration file <cfngin-config>` **[REQUIRED]**
- a key/value :ref:`environment file <cfngin-env>`



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

Runway can pass :ref:`Parameters <term-param>` to a CloudFormation module in place of or in addition to an :ref:`environment file <cfngin-env>`.
When :ref:`Parameters <term-param>` are passed to the module, the data type is retained (e.g. ``array``, ``boolean``, ``mapping``).

A typical usage pattern would be to use :ref:`Runway Lookups <Lookups>` in combination with :ref:`Parameters <term-param>` to pass :ref:`deploy environment <term-deploy-env>` and/or region specific values to the module from the `Runway Config File`_.

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

Runway automatically makes the following commonly used :ref:`Parameters <term-param>`  available to CloudFormation modules.

.. note::
  If these parameter names are already being explicitly defined in the `Runway Config File`_ or :ref:`environment file <cfngin-env>`.
  The value provided will be used over that which would be automatically added.

**environment (str)**
  Taken from the ``DEPLOY_ENVIRONMENT`` environment variable. This will the be current :ref:`deploy environment <term-deploy-env>`.

**region (str)**
  Taken from the ``AWS_REGION`` environment variable. This will be the current region being processed.



----

.. _cfngin-config:

******************
CFNgin Config File
******************

Runway's CFNgin makes use of a YAML formatted config file to define the different
CloudFormation stacks that make up a given environment.

The configuration file has a loose definition, with only a few top-level keywords.
Other than those keywords, you can define your own top-level keys to make use of other YAML features like
`anchors & references <https://en.wikipedia.org/wiki/YAML#Repeated_nodes>`_ to avoid duplicating config.
(See :ref:`YAML anchors & references <cfngin-yaml>` for details)


Top Level Keywords
==================

.. _cfngin-namespace:

Namespace
---------

You can provide a   ``namespace`` to create all stacks within. The namespace_ will
be used as a prefix for the name of any stack that Runway's CFNgin creates.

In addition, this value will be used to create an S3 bucket that Runway's CFNgin will
use to upload and store all CloudFormation templates.

In general, this is paired with the concept of :ref:`Environments <term-cfngin-env>` to create a namespace_ per environment.

.. code-block:: yaml

  namespace: ${namespace}


Namespace Delimiter
-------------------

By default, Runway's CFNgin will use ``-`` as a delimiter between your namespace_ and the
declared stack name to build the actual CloudFormation stack name that gets
created. Since child resources of your stacks will, by default, use a portion
of your stack name in the auto-generated resource names, the first characters
of your fully-qualified stack name potentially convey valuable information to
someone glancing at resource names. If you prefer to not use a delimiter, you
can pass the ``namespace_delimiter`` top-level keyword in the config as an empty string.

See the `CloudFormation API Reference <http://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStack.html>`__ for allowed stack name characters


.. _cfngin-bucket:
.. _stacker_bucket:

S3 Bucket
---------

Runway's CFNgin, by default, pushes your CloudFormation templates into an S3 bucket
and points CloudFormation at the template in that bucket when launching or
updating your stacks. By default it uses a bucket named
``stacker-${namespace}``, where the namespace_ is the namespace_ provided the
config.

If you want to change this, provide the ``cfngin_bucket`` top-level keyword
in the config.

The bucket will be created in the same region that the stacks will be launched
in.  If you want to change this, or if you already have an existing bucket
in a different region, you can set the ``cfngin_bucket_region`` to
the region where you want to create the bucket.

If you want CFNgin to upload templates directly to CloudFormation, instead of
first uploading to S3, you can set ``cfngin_bucket`` to an empty string.
However, note that template size is greatly limited when uploading directly.
See the `CloudFormation Limits Reference <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cloudformation-limits.html>`__.


Persistent Graph
----------------

Each time Runway's CFNgin is run, it creates a dependency :ref:`graph <term-graph>` of :ref:`Stacks <term-stack>`.
This is used to determine the order in which to execute them. This :ref:`graph <term-graph>` can be
persisted between runs to track the removal of :ref:`Stacks <term-stack>` the config file.

When a :ref:`stack <term-stack>` is present in the persistent graph but not in the :ref:`graph <term-graph>`
constructed from the config file, CFNgin will delete the :ref:`stack <term-stack>` from
CloudFormation. This takes effect during both build and destroy actions.

To enable persistent graph, set **persistent_graph_key** to a unique value
that will be used to construct the path to the persistent graph object in S3.
This object is stored in the CFNgin `S3 Bucket`_ which is also used for
CloudFormation templates. The fully qualified path to the object will look
like the below.

.. code-block::

  s3://${cfngin_bucket}/${namespace}/persistent_graphs/${namespace}/${persistent_graph_key}.json

.. note::
  It is recommended to enable versioning on the CFNgin `S3 Bucket`_ when
  using persistent graph to have a backup version in the event something
  unintended happens. A warning will be logged if this is not enabled.

  If CFNgin creates an `S3 Bucket`_ for you when persistent graph is enabled,
  it will be created with versioning enabled.

.. important::
  When choosing a value for **persistent_graph_key**, it is vital to ensure
  the value is unique for the **namespace** being used. If the key is a
  duplicate, `stacks <../terminology.html#stack>`_ that are not intended to be
  destroyed will be destroyed.

When executing an action that will be modifying the persistent graph
(build or destroy), the S3 object is *"locked"*. The lock is a tag applied to
the object at the start of one of these actions. The tag-key is
**cfngin_lock_code** and the tag-value is UUID generated each time a command
is run. In order for Runway's CFNgin to lock a persistent graph object, the tag must
not be present on the object. For Runway's CFNgin to act on the :ref:`graph <term-graph>` (modify or
unlock) the value of the tag must match the UUID of the current CFNgin
session. If the object is locked or the code does not match, an error will be
raised and no action will be taken. This prevents two parties from acting on
the same persistent graph object concurrently which would create a race
condition.

.. note::
  A persistent graph object can be unlocked manually by removing the
  **cfngin_lock_code** tag from it. This should be done with caution as it
  will cause any active sessions to raise an error.


Persistent Graph Example
~~~~~~~~~~~~~~~~~~~~~~~~

.. rubric:: config.yml
.. code-block:: yaml

  namespace: example
  cfngin_bucket: cfngin-bucket
  persistent_graph_key: my_graph  # .json - will be appended if not provided
  stacks:
    first_stack:
      ...
    new_stack:
      ...

.. rubric:: s3://cfngin-bucket/persistent_graphs/example/my_graph.json
.. code-block:: json

  {
    "first_stack": [],
    "removed_stack": [
      "first_stack"
    ]
  }

.. rubric:: Result

Given the above config file and persistent graph,
when running ``runway deploy``, the following will occur.

#. The ``{"Key": "cfngin_lock_code", "Value": "123456"}`` tag is applied to
   **s3://cfngin-bucket/persistent_graphs/example/my_graph.json** to lock it
   to the current session.
#. **removed_stack** is deleted from CloudFormation and deleted from the
   persistent graph object in S3.
#. **first_stack** is updated in CloudFormation and updated in the persistent
   graph object in S3 (incase dependencies change).
#. **new_stack** is created in CloudFormation and added to the persistent graph
   object in S3.
#. The ``{"Key": "cfngin_lock_code", "Value": "123456"}`` tag is removed from
   **s3://cfngin-bucket/persistent_graphs/example/my_graph.json** to unlock it
   for use in other sessions.


Module Paths
------------

When setting the ``classpath`` for :ref:`Blueprints`/:ref:`hooks <term-cfngin-hook>`,
it is sometimes desirable to load modules from outside the default ``sys.path``
(e.g., to include modules inside the same repo as config files).

Adding a path (e.g. ``./``) to the ``sys_path`` top-level keyword will allow
modules from that path location to be used.


Service Role
------------

By default Runway's CFNgin doesn't specify a service role when executing changes to
CloudFormation stacks. If you would prefer that it do so, you can set
``service_role`` to be the ARN of the role that CFNgin should use when
executing CloudFormation changes.

This is the equivalent of setting ``RoleARN`` on a call to the following
CloudFormation api calls: ``CreateStack``, ``UpdateStack``,
``CreateChangeSet``.

See the AWS documentation for `AWS CloudFormation Service Roles <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html?icmpid=docs_cfn_console>`__.


Remote Packages
---------------

The ``package_sources`` top-level keyword can be used to define remote
sources for :ref:`Blueprints` (e.g., retrieving ``src/runway/blueprints`` on github at
tag ``v1.3.7``).

The only required key for a git repository config is ``uri``, but ``branch``,
``tag``, & ``commit`` can also be specified.

.. code-block:: yaml

  package_sources:
    git:
      - uri: git@github.com:onicagroup/runway.git
      - uri: git@github.com:onicagroup/runway.git
        tag: 1.0.0
        paths:
          - src/runway/blueprints
      - uri: git@github.com:contoso/webapp.git
        branch: staging
      - uri: git@github.com:contoso/foo.git
        commit: 12345678

If no specific commit or tag is specified for a repo, the remote repository
will be checked for newer commits on every execution of CFNgin.

For ``.tar.gz`` & ``zip`` archives on s3, specify a ``bucket`` & ``key``.

.. code-block:: yaml

  package_sources:
    s3:
      - bucket: mycfngins3bucket
        key: archives/blueprints-v1.zip
        paths:
          - blueprints
      - bucket: anothers3bucket
        key: public/public-blueprints-v2.tar.gz
        requester_pays: true
      - bucket: yetanothers3bucket
        key: sallys-blueprints-v1.tar.gz
        # use_latest defaults to true - will update local copy if the
        # last modified date on S3 changes
        use_latest: false

Local directories can also be specified.

.. code-block:: yaml

  package_sources:
    local:
      - source: ../vpc

Use the ``paths`` option when subdirectories of the repo/archive/directory
should be added to CFNgins's ``sys.path``.

Cloned repos/archives will be cached between builds; the cache location defaults
to ``~/.runway_cache`` but can be manually specified via the ``cfngin_cache_dir``
top-level keyword.


Remote Configs
~~~~~~~~~~~~~~

Configuration YAMLs from remote configs can also be used by specifying a list
of ``configs`` in the repo to use.

.. code-block:: yaml

  package_sources:
    git:
      - uri: git@github.com:acmecorp/cfngin_blueprints.git
        configs:
          - vpc.yaml

In this example, the configuration in ``vpc.yaml`` will be merged into the
running current configuration, with the current configuration's values taking
priority over the values in ``vpc.yaml``.

Dictionary Stack Names & Hook Paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To allow remote configs to be selectively overridden, stack names & :ref:`hook <term-cfngin-hook>` paths are defined as dictionaries.

.. code-block:: yaml

  pre_build:
    my_route53_hook:
      path: runway.cfngin.hooks.route53.create_domain:
      required: true
      enabled: true
      args:
        domain: mydomain.com
  stacks:
    vpc-example:
      class_path: cfngin_blueprints.vpc.VPC
      locked: false
      enabled: true
    bastion-example:
      class_path: cfngin_blueprints.bastion.Bastion
      locked: false
      enabled: true


Pre & Post Hooks
----------------

Many actions allow for pre & post :ref:`hooks <term-cfngin-hook>`. These are python functions/methods that are
executed before, and after the action is taken for the entire config. :ref:`Hooks <term-cfngin-hook>`
can be enabled or disabled, per :ref:`hook <term-cfngin-hook>`. Only the following actions allow
pre/post :ref:`hooks <term-cfngin-hook>`:

* build (keywords: ``pre_build``, ``post_build``)
* destroy (keywords: ``pre_destroy``, ``post_destroy``)

There are a few reasons to use these, though the most common is if you want
better control over the naming of a resource than what CloudFormation allows.

The keyword is a dictionary with the following keys:

**path:**
  the python import path to the :ref:`hook <term-cfngin-hook>`.

**data_key:**
  If set, and the :ref:`hook <term-cfngin-hook>` returns data (a dictionary), the results will be stored
  in the ``context.hook_data`` with the ``data_key`` as its key.

**required:**
  Whether to stop execution if the :ref:`hook <term-cfngin-hook>` fails.

**enabled:**
  Whether to execute the :ref:`hook <term-cfngin-hook>` every CFNgin run. Default: True. This is a bool
  that grants you the ability to execute a :ref:`hook <term-cfngin-hook>` per environment when combined
  with a variable pulled from an environment file.

**args:**
  A dictionary of arguments to pass to the :ref:`hook <term-cfngin-hook>` with support for :ref:`lookups <cfngin-lookups>`.
  Note that :ref:`lookups <cfngin-lookups>` that change the order of execution, like ``output``, can
  only be used in a `post` hook but hooks like ``rxref`` are able to be used
  with either `pre` or `post` hooks.

An example using the ``create_domain`` :ref:`hook <term-cfngin-hook>` for creating a route53 domain before
the build action:

.. code-block:: yaml

  pre_build:
    create_my_domain:
      path: runway.cfngin.hooks.route53.create_domain
      required: true
      enabled: true
      args:
        domain: mydomain.com

An example of a :ref:`hook <term-cfngin-hook>` using the ``create_domain_bool`` variable from the environment
file to determine if the :ref:`hook <term-cfngin-hook>` should run. Set ``create_domain_bool: true`` or
``create_domain_bool: false`` in the environment file to determine if the :ref:`hook <term-cfngin-hook>`
should run in the environment CFNgin is running against:

.. code-block:: yaml

  pre_build:
    create_my_domain:
      path: runway.cfngin.hooks.route53.create_domain
      required: true
      enabled: ${create_domain_bool}
      args:
        domain: mydomain.com

An example of a custom hooks using various lookups in it's arguments:

.. code-block:: yaml

  pre_build:
    custom_hook1:
      path: path.to.hook1.entry_point
      args:
        ami: ${ami [<region>@]owners:self,888888888888,amazon name_regex:server[0-9]+ architecture:i386}
        user_data: ${file parameterized-64:file://some/path}
        db_endpoint: ${rxref some-stack::Endpoint}
        subnet: ${xref some-stack::Subnet}
        db_creds: ${ssm MyDBUser::region=us-east-1}
    custom_hook2:
      path: path.to.hook.entry_point
      args:
        bucket: ${dynamodb us-east-1:TestTable@TestKey:TestVal.BucketName}
        bucket_region: ${envvar AWS_REGION}  # this variable is set by Runway
        files:
          - ${file plain:file://some/path}

  post_build:
    custom_hook3:
      path: path.to.hook3.entry_point
      args:
        nlb: ${output nlb-stack::Nlb}  # output can only be used as a post hook


Tags
----

CloudFormation supports arbitrary key-value pair tags. All stack-level, including automatically created tags, are
propagated to resources that AWS CloudFormation supports. See `AWS CloudFormation Resource Tags Type`_ for more details.
If no tags are specified, the ``cfngin_namespace`` tag is applied to your stack with the value of ``namespace`` as the
tag value.

If you prefer to apply a custom set of tags, specify the top-level keyword ``tags`` as a map.

.. rubric:: Example:
.. code-block:: yaml

  tags:
    "hello": world
    "my_tag:with_colons_in_key": ${dynamic_tag_value_from_my_env}
    simple_tag: simple value

If you prefer to have no tags applied to your stacks (versus the default tags that CFNgin applies), specify an empty
map for the top-level keyword.

.. code-block:: yaml

  tags: {}

.. _`AWS CloudFormation Resource Tags Type`: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-resource-tags.html


Mappings
--------

Mappings are dictionaries that are provided as `Mappings <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/mappings-section-structure.html>`__ to each CloudFormation stack that CFNgin produces.

These can be useful for providing things like different AMIs for different
instance types in different regions.

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

These can be used in each :ref:`Blueprint`/stack as usual.


Lookups
-------

Lookups allow you to create custom methods which take a value and are
resolved at build time. The resolved values are passed to the :ref:`Blueprint` before it is rendered.
For more information, see the :ref:`Lookups <cfngin-lookups>` documentation.

CFNgin provides some common :ref:`Lookups <cfngin-lookups>`, but it is
sometimes useful to have your own custom lookup that doesn't get shipped
with Runway. You can register your own lookups by defining a ``lookups``
key.

.. code-block:: yaml

  lookups:
    custom: path.to.lookup.handler

The key name for the lookup will be used as the type name when registering
the lookup. The value should be the path to a valid lookup handler.

You can then use these within your config.

.. code-block:: yaml

  conf_value: ${custom some-input-here}


Stacks
------

This is the core part of the config - this is where you define each of the
stacks that will be deployed in the environment.  The top-level keyword
``stacks`` is populated with a dictionary, each representing a single
stack to be built.

They key used in the dictionary of stacks is used as the logical name of the stack.
The value here must be unique within the config.
If no ``stack_name`` is provided, the value here will be used for the name of the CloudFormation stack.

A stack has the following keys:

**class_path (Optional[str])**
  The python class path to the :ref:`Blueprint` to be used. Specify this or
  ``template_path`` for the stack.

**description (Optional[str])**
  A short description to apply to the stack. This overwrites any description
  provided in the :ref:`Blueprint`. See:
  http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-description-structure.html

**enabled (Optional[bool])**
  If set to ``false``, the stack is disabled, and will not be
  built or updated. This can allow you to disable stacks in different
  environments. (*default:* ``true``)

**in_progress_behavior (Optional[str])**
  If provided, specifies the behavior for when a stack is in
  ``CREATE_IN_PROGRESS`` or ``UPDATE_IN_PROGRESS``. By default, CFNgin will raise
  an exception if the stack is in an ``IN_PROGRESS`` state. You can set this
  option to ``wait`` and CFNgin will wait for the previous update to complete
  before attempting to update the stack.

**locked (Optional[bool])**
  If set to ``true``, the stack is locked and will not be
  updated unless the stack is passed to CFNgin via the ``--force`` flag.
  This is useful for **risky** stacks that you don't want to take the
  risk of allowing CloudFormation to update, but still want to make
  sure get launched when the environment is first created. When ``locked``,
  it's not necessary to specify a ``class_path`` or ``template_path``.
  (*default:* ``false``)

**protected (Optional[bool])**
  When running an update in non-interactive mode, if a stack has
  ``protected: true`` and would get changed, CFNgin will switch to
  interactive mode for that stack, allowing you to approve/skip the change.
  (*default:* ``false``)

**required_by (Optional[List[str]])**
  A list of other stacks or targets that require this stack. It's an
  inverse to ``requires``.

**requires (Optional[List[str]])**
  A list of other stacks this stack requires. This is for explicit
  dependencies - you do not need to set this if you refer to another stack in
  a Parameter, so this is rarely necessary.

**stack_name (Optional[str])**
  If provided, this will be used as the name of the CloudFormation
  stack. Unlike ``name``, the value doesn't need to be unique within the config,
  since you could have multiple stacks with the same name, but in different
  regions or accounts. (note: the namespace from the environment will be
  prepended to this)

**stack_policy_path (Optional[str])**
  If provided, specifies the path to a JSON formatted stack policy
  that will be applied when the CloudFormation stack is created and updated.
  You can use stack policies to prevent CloudFormation from making updates to
  protected resources (e.g. databases). See: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html

**tags (Optional[Dict[str, str]])**
  A dictionary of CloudFormation tags to apply to this stack. This
  will be combined with the global tags, but these tags will take precedence.

**template_path (Optional[str])**
  Path to raw CloudFormation template (JSON or YAML). Specify this or
  ``class_path`` for the stack. Path can be specified relative to the current
  working directory (e.g. templates stored alongside the Config), or relative
  to a directory in the python ``sys.path`` (i.e. for loading templates
  retrieved via ``packages_sources``).

**termination_protection (Optional[bool])**
  If ``true``, the stack will be protected from termination by CloudFormation.
  Any attempts to destroy the stack (using Runway, the AWS Console, AWS API, etc) will be prevented unless manually disabled.
  When updating a stack and the value has been changed to ``false``, termination protection will be disabled.
  (*default:* ``false``)

**variables (Optional[Dict[str, str]])**
  A dictionary of Variables_ to pass into the :ref:`Blueprint` when rendering the
  CloudFormation template. Variables_ can be any valid YAML data
  structure.


Stacks Example
~~~~~~~~~~~~~~

Here's an example used to create a VPC:

.. code-block:: yaml

  stacks:
    - name: vpc-example
      class_path: blueprints.vpc.VPC
      locked: false
      enabled: true
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


Custom Log Formats
------------------

By default, Runway's CFNgin uses the following ``log_formats``:

.. code-block:: yaml

  log_formats:
    info: "[%(asctime)s] %(message)s"
    color: "[%(asctime)s] \033[%(color)sm%(message)s\033[39m"
    debug: "[%(asctime)s] %(levelname)s %(threadName)s %(name)s:%(lineno)d(%(funcName)s): %(message)s"

You may optionally provide custom `log_formats`. In this example, we add the environment name to each log line.

.. code-block:: yaml

  log_formats:
    info: "[%(asctime)s] ${environment} %(message)s"
    color: "[%(asctime)s] ${environment} \033[%(color)sm%(message)s\033[39m"

You may use any of the standard Python
`logging module format attributes <https://docs.python.org/2.7/library/logging.html#logrecord-attributes>`_
when building your `log_formats`.


Variables
==========

Variables are values that will be passed into a :ref:`Blueprint` before it is
rendered. Variables can be any valid YAML data structure and can leverage
:ref:`Lookups <cfngin-lookups>` to expand values at build time.

The following concepts make working with variables within large templates
easier:

.. _cfngin-yaml:

YAML anchors & references
-------------------------

If you have a common set of variables that you need to pass around in many
places, it can be annoying to have to copy and paste them in multiple places.
Instead, using a feature of YAML known as `anchors & references`_, you can
define common values in a single place and then refer to them with a simple
syntax.

For example, say you pass a common domain name to each of your stacks, each of
them taking it as a Variable. Rather than having to enter the domain into
each stack (and hopefully not typo'ing any of them) you could do the
following:

.. code-block:: yaml

  domain_name: &domain mydomain.com

Now you have an anchor called **domain** that you can use in place of any value
in the config to provide the value **mydomain.com**. You use the anchor with
a reference.

.. code-block:: yaml

  stacks:
    - name: vpc
      class_path: blueprints.vpc.VPC
      variables:
        DomainName: *domain

Even more powerful is the ability to anchor entire dictionaries, and then
reference them in another dictionary, effectively providing it with default
values.

.. code-block:: yaml

  common_variables: &common_variables
    DomainName: mydomain.com
    InstanceType: m3.medium
    AMI: ami-12345abc

Now, rather than having to provide each of those variables to every stack that
could use them, you can just do this instead.

.. code-block:: yaml

  stacks:
    - name: vpc
      class_path: blueprints.vpc.VPC
      variables:
        << : *common_variables
        InstanceType: c4.xlarge # override the InstanceType in this stack


Using Outputs as Variables
---------------------------

Since Runway's CFNgin encourages the breaking up of your CloudFormation stacks into
entirely separate stacks, sometimes you'll need to pass values from one stack
to another. The way this is handled in CFNgin is by having one stack
provide :ref:`Outputs <term-outputs>` for all the values that another stack may need, and then
using those as the inputs for another stack's Variables_. CFNgin makes
this easier for you by providing a syntax for Variables_ that will cause
CFNgin to automatically look up the values of :ref:`Outputs <term-outputs>` from another stack
in its config. To do so, use the following format for the Variable on the
target stack.

.. code-block:: yaml

  MyParameter: ${output OtherStack::OutputName}

Since referencing :ref:`Outputs <term-outputs>` from stacks is the most common use case, ``output`` is the default lookup type.
For more information see :ref:`Lookups <cfngin-lookups>`.

In this example config - when building things inside a VPC, you will need to pass the **VpcId** of the VPC that you want the resources to be located in.
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
        VpcId: ${output vpc::VpcId} # gets the VpcId Output from the vpc stack

Note: Doing this creates an implicit dependency from the **webservers** stack
to the **vpc** stack, which will cause CFNgin to submit the **vpc** stack, and
then wait until it is complete until it submits the **webservers** stack.



----

.. _cfngin-env:

****************
Environment File
****************

When using Runway's CFNgin, you can optionally provide an "environment" file. The
CFNgin config file will be interpolated as a `string.Template
<https://docs.python.org/2/library/string.html#template-strings>`_ using the
key/value pairs from the environment file. The format of the file is a single
key/value per line, separated by a colon (**:**).


File Naming
===========

Environment files must follow a specific naming format in order to be recognized by Runway.
The files must also be stored at the root of the module's directory.

**<DEPLOY_ENVIRONMENT>-<AWS_REGION>.env**
  The typical naming format that will be used for these files specifies the name of the ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` in which to use the file.

**<DEPLOY_ENVIRONMENT>.env**
  The region can optionally be omitted to apply a single file to all regions.

Files following both naming schemes may be used. The file with the most specific name takes precedence.
Values passed in as ``parameters`` from the `Runway Config File`_ take precedence over those provided in an environment file.


Usage
=====

A pretty common use case is to have separate environments that you want to
look mostly the same, though with some slight modifications. For example, you
might want a **production** and a **staging** environment. The production
environment likely needs more instances, and often those instances will be
of a larger instance type. :ref:`Environments <term-cfngin-env>` allow you to use your existing
CFNgin config, but provide different values based on the environment file
chosen.

.. rubric:: Example
.. code-block:: yaml

  vpcID: vpc-12345678

Provided the key/value vpcID above, you will now be able to use this in
your configs for the specific environment you are deploying into. They
act as keys that can be used in your config file, providing a sort of
templating ability. This allows you to change the values of your config
based on the environment you are in. For example, if you have a **webserver**
stack, and you need to provide it a variable for the instance size it
should use, you would have something like this in your config file.

.. code-block:: yaml

  stacks:
    - name: webservers
      class_path: blueprints.asg.AutoscalingGroup
      variables:
        InstanceType: m3.medium

But what if you needed more CPU in your production environment, but not in your
staging? Without Environments, you'd need a separate config for each. With
environments, you can simply define two different environment files with the
appropriate **InstanceType** in each, and then use the key in the environment
files in your config.

.. code-block:: yaml

  # in the file: stage.env
  web_instance_type: m3.medium

  # in the file: prod.env
  web_instance_type: c4.xlarge

  # in your config file:
  stacks:
    - name: webservers
      class_path: blueprints.asg.AutoscalingGroup
      variables:
        InstanceType: ${web_instance_type}
