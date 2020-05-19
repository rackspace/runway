.. _Runway Config File: runway_config.html

#################
Advanced Features
#################

Advanced features and detailed information for using Terraform with Runway.

.. _tf-backend:

*********************
Backend Configuration
*********************

If your Terraform will only ever be used with a single backend, it can be defined inline.

.. rubric:: main.tf
.. code-block::

  terraform {
    backend "s3" {
      region = "us-east-1"
      key = "some_unique_identifier_for_my_module" # e.g. contosovpc
      bucket = "some_s3_bucket_name"
      dynamodb_table = "some_ddb_table_name"
    }
  }

However, it's generally preferable to separate the backend configuration out from the rest of the Terraform code.
Choose from one of the following options.


Backend Config File
===================

Backend config options can be specified in a separate file or multiple files per environment and/or region using one of the following naming schemes.

- ``backend-ENV-REGION.tfvars``
- ``backend-ENV.tfvars``
- ``backend-REGION.tfvars``
- ``backend.tfvars``

.. rubric:: Example
.. code-block::

  region = "us-east-1"
  bucket = "some_s3_bucket_name"
  dynamodb_table = "some_ddb_table_name"

In the above example, where all but the key are defined, the **main.tf** backend definition is reduced to the following.

.. rubric:: main.tf
.. code-block::

  terraform {
    backend "s3" {
      key = "some_unique_identifier_for_my_module" # e.g. contosovpc
    }
  }


runway.yml
==========

Backend config options can also be specified as a module option in the `Runway Config File`_.
:ref:`Lookups` can be used to provide dynamic values to this option.

.. rubric:: Module Level
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp.tf
          options:
            terraform_backend_config:
              bucket: mybucket
              dynamodb_table: mytable
              region: us-east-1

.. rubric:: Deployment Level
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp-01.tf
        - path: sampleapp-02.tf
      module_options:  # shared between all modules in deployment
        terraform_backend_config:
          bucket: ${ssm ParamNameHere::region=us-east-1}
          dynamodb_table: ${ssm ParamNameHere::region=us-east-1}
          region: ${env AWS_REGION}


runway.yml From CloudFormation Outputs
======================================

A recommended option for managing the state bucket and table is to create
them via CloudFormation (try running ``runway gen-sample cfn`` to get a
template and stack definition for bucket/table stack). To further support this,
backend config options can be looked up directly from CloudFormation
outputs.

.. rubric:: Module Level
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp.tf
          options:
            terraform_backend_config:
              region: us-east-1
            terraform_backend_cfn_outputs:
              bucket: StackName::OutputName  # e.g. common-tf-state::TerraformStateBucketName
              dynamodb_table: StackName::OutputName  # e.g. common-tf-state::TerraformStateTableName


.. rubric:: Deployment Level
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp-01.tf
        - path: sampleapp-02.tf
      module_options:  # shared between all modules in deployment
        terraform_backend_config:
          region: us-east-1
        terraform_backend_cfn_outputs:
          bucket: StackName::OutputName  # e.g. common-tf-state::TerraformStateBucketName
          dynamodb_table: StackName::OutputName  # e.g. common-tf-state::TerraformLockTableName


----


.. _tf-args:

******************************************
Specifying Terraform CLI Arguments/Options
******************************************

Runway can pass custom arguments/options to the Terraform CLI by using the ``args`` option.

The value of ``args`` can be provided in one of two ways.
The simplest way is to provide a *list* of arguments/options which will be appended to ``terraform apply`` when executed by Runway.
Each element of the argument/option should be it's own list item (e.g. ``-parallelism=25 -no-color`` would be ``['-parallelism=25, '-no-color']``).

For more control, a map can be provided to pass arguments/options to other commands.
Arguments can be passed to ``terraform apply``, ``terraform init``, and/or ``terraform plan`` by using the *action* as the key in the map (see the **Runway Example** section below).
The value of each key in the map must be a list as described in the previous section.

.. important::
  The following arguments/options are provided by Runway and should not be provided manually:
  *auto-approve*, *backend-config*, *force*, *no-color*, *reconfigure*, *update*, and *var-file*.
  Providing any of these manually could result in unintended side-effects.


.. rubric:: Runway Example
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp-01.tf
          options:
            args:
              - '-no-color'
              - '-parallelism=25'
        - path: sampleapp-02.tf
          options:
            args:
              apply:
                - '-no-color'
                - '-parallelism=25'
              init:
                - '-no-color'
              plan:
                - '-no-color'
                - '-parallelism=25'
      regions:
        - us-east-2
      environments:
        example: true

.. rubric:: Command Equivalent
.. code-block::

  # runway deploy - sampleapp-01.tf
  terraform init -reconfigure
  terraform apply -no-color -parallelism=25 -auto-approve=false

  # runway plan - sampleapp-01.tf
  terraform plan

.. code-block::

  # runway deploy - sampleapp-02.tf
  terraform init -reconfigure -no-color
  terraform apply -no-color -parallelism=25 -auto-approve=false

  # runway plan - sampleapp-02.tf
  terraform plan -no-color -parallelism=25


----


.. _tf-version:

******************
Version Management
******************

By specifying which version of Terraform to use via a ``.terraform-version`` file in your module directory, or a module
option, Runway will automatically download & use that version for the module. This, alongside
tightly pinning Terraform provider versions, is highly recommended to keep a predictable experience
when deploying your module.

.. rubric:: .terraform-version
.. code-block::

  0.11.6

.. rubric:: runway.yml
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp-01.tf
          options:
            terraform_version: 0.11.13
        - path: sampleapp-02.tf
          options:
            terraform_version:
              "*": 0.11.13  # applies to all environments
              # prod: 0.9.0  # can also be specified for a specific environment

Without a version specified, Runway will fallback to whatever ``terraform`` it finds first in your PATH.
