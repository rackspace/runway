.. _CFNgin: ../cfngin/index.html
.. _CFNgin Config File: ../cfngin/config.html
.. _deploy environment: ../terminology.rst#deploy-environment
.. _environment file: ../cfngin/environments.html
.. _Lookups: lookups.html
.. _Parameters: ../terminology.html#parameters
.. _Runway Config File: runway_config.html

.. _mod-cfn:

CloudFormation
==============

CloudFormation modules are processed using CFNgin.
There are two files that can be used for configuration:

- a YAML `CFNgin Config File`_
- an optional key/value `environment file`_


.. rubric:: Environment

Name these files in the form of ``ENV-REGION.env`` (e.g. ``dev-us-east-1.env``) or ``ENV.env`` (e.g. ``dev.env``):

.. code-block:: yaml

  # Namespace is used as each stack's prefix
  # We recommend an (org/customer)/environment delineation
  namespace: contoso-dev
  environment: dev
  customer: contoso
  region: us-west-2
  # The stacker bucket is the S3 bucket (automatically created) where templates
  # are uploaded for deployment (a CloudFormation requirement for large templates)
  stacker_bucket_name: stacker-contoso-us-west-2

.. rubric:: Stack Config (yaml file)

These files can have any name ending in .yaml (they will be evaluated in alphabetical order):

.. code-block:: yaml

  # Note namespace/stacker_bucket_name being substituted from the environment
  namespace: ${namespace}
  stacker_bucket: ${stacker_bucket_name}

  stacks:
    myvpcstack:  # will be deployed as contoso-dev-myvpcstack
      template_path: templates/vpc.yaml
      # The enabled option is optional and defaults to true. You can use it to
      # enable/disable stacks per-environment (i.e. like the namespace
      # substitution above, but with the value of either true or false for the
      # enabled option here)
      enabled: true
    myvpcendpoint:
      template_path: templates/vpcendpoint.yaml
      # variables map directly to CFN parameters; here used to supply the
      # VpcId output from the myvpcstack to the VpcId parameter of this stack
      variables:
        VpcId: ${output myvpcstack::VpcId}

The config yaml supports many more features; see the full CFNgin_ documentation for more detail
(e.g. stack configuration options, additional lookups in addition to output (e.g. SSM, DynamoDB))


Parameters
----------

Runway can pass Parameters_ to a CloudFormation module in place of or in addition to an `environment file`_.
When Parameters_ are passed to the module, the data type is retained (e.g. ``array``, ``boolean``, ``mapping``).

A typical usage pattern would be to use Lookups_ in combination with Parameters_ to pass `deploy environment`_ and/or
region specific values to the module from the `Runway Config File`_.

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
~~~~~~~~~~~~~~~~~

Runway automatically makes the following commonly used Parameters_ available to CloudFormation modules.

.. note:: If these parameter names are already being explicitly defined in the `Runway Config File`_
          or `environment file`_ the value provided will be used over that which would be automatically added.

**environment (str)**
  Taken from the ``DEPLOY_ENVIRONMENT`` environment variable. This will the be current `deploy environment`_.

**region (str)**
  Taken from the ``AWS_REGION`` environment variable. This will be the current region being processed.


Top-level Runway Config
-----------------------

.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: mycfnstacks
          parameters:
            namespace: contoso-${env DEPLOY_ENVIRONMENT}
            foo: bar
            some_value: ${var some_map.${env DEPLOY_ENVIRONMENT}}

and/or

.. code-block:: yaml

  ---
  deployments:
    - parameters:
        namespace: contoso-${env DEPLOY_ENVIRONMENT}
        foo: bar
        some_value: ${var some_map.${env DEPLOY_ENVIRONMENT}}
      modules:
        - mycfnstacks


In Module Directory
-------------------

.. important: `Lookups`_ are not supported in this file.

.. code-block:: yaml

  ---
  parameters:
    namespace: contoso-dev
    foo: bar

(in ``runway.module.yml``)
