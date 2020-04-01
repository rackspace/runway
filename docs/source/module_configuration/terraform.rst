.. _Lookups: lookups.html

.. _mod-tf:

Terraform
=========

Runway provides a simple way to run the Terraform versions you want with
variable values specific to each environment. Perform the following steps to
align your Terraform directory with Runway's requirements & best practices.


Part 1: Adding Terraform to Deployment
--------------------------------------

Start by adding your Terraform directory to your r4y.yml's list of modules.

(Note: to Runway, a module is just a directory in which to run
``terraform apply``, ``serverless deploy``, etc - no relation to Terraform's
concept of modules)

Directory tree:
::

    .
    ├── r4y.yml
    └── terraformstuff.tf
        └── main.tf


r4y.yml:
::

    ---
    deployments:
      - modules:
          - terraformstuff.tf
        regions:
          - us-east-1


Part 2: Specify the Terraform Version
-------------------------------------

By specifying the version via a ``.terraform-version`` file in your Terraform directory, or a module
option, Runway will automatically download & use that version for the module. This, alongside
tightly pinning Terraform provider versions, is highly recommended to keep a predictable experience
when deploying your module.

.terraform-version::

    0.11.6


or in r4y.yml, either for a single module::

    ---
    deployments:
      - modules:
          - path: mytfmodule
            options:
              terraform_version:
                "*": 0.11.13  # applies to all environments
                # prod: 0.9.0  # can also be specified for a specific environment


and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: mytfmodule
          - path: anothermytfmodule
        module_options:  # shared between all modules in deployment
          terraform_version:
            "*": 0.11.13  # applies to all environments
            # prod: 0.9.0  # can also be specified for a specific environment


Without a version specified, Runway will fallback to whatever ``terraform``
it finds first in your PATH.


Part 3: Adding Backend Configuration
------------------------------------

Next, configure the backend for your Terraform configuration. If your Terraform
will only ever be used with a single backend, it can be defined inline:

main.tf:
::

    terraform {
      backend "s3" {
        region = "us-east-1"
        key = "some_unique_identifier_for_my_module" # e.g. contosovpc
        bucket = "some_s3_bucket_name"
        dynamodb_table = "some_ddb_table_name"
      }
    }

However, it's generally preferable to separate the backend configuration out
from the rest of the Terraform code. Choose from one of the following options.


Backend Config in File
~~~~~~~~~~~~~~~~~~~~~~

Backend config options can be specified in a separate file or multiple files
per environment and/or region:

- ``backend-ENV-REGION.tfvars``
- ``backend-ENV.tfvars``
- ``backend-REGION.tfvars``
- ``backend.tfvars``

::

        region = "us-east-1"
        bucket = "some_s3_bucket_name"
        dynamodb_table = "some_ddb_table_name"

In the above example, where all but the key are defined, the main.tf backend
definition is reduced to:

main.tf::

    terraform {
      backend "s3" {
        key = "some_unique_identifier_for_my_module" # e.g. contosovpc
      }
    }


Backend Config in r4y.yml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Backend config options can also be specified as a module option in r4y.yml:

Either for a single module::

    ---
    deployments:
      - modules:
          - path: mytfmodule
            options:
              terraform_backend_config:
                bucket: mybucket
                region: us-east-1
                dynamodb_table: mytable

and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: mytfmodule
          - path: anothermytfmodule
        module_options:  # shared between all modules in deployment
          terraform_backend_config:
            bucket: mybucket
            region: us-east-1
            dynamodb_table: mytable


Backend CloudFormation Outputs in r4y.yml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A recommended option for managing the state bucket and table is to create
them via CloudFormation (try running ``r4y gen-sample cfn`` to get a
template and stack definition for bucket/table stack). To further support this,
backend config options can be looked up directly from CloudFormation
outputs.

Either for a single module::

    ---
    deployments:
      - modules:
          - path: mytfmodule
            options:
              terraform_backend_config:
                region: us-east-1
              terraform_backend_cfn_outputs:
                bucket: StackName::OutputName  # e.g. common-tf-state::TerraformStateBucketName
                dynamodb_table: StackName::OutputName  # e.g. common-tf-state::TerraformStateTableName


and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: mytfmodule
          - path: anothermytfmodule
        module_options:  # shared between all modules in deployment
          terraform_backend_config:
            region: us-east-1
          terraform_backend_cfn_outputs:
            bucket: StackName::OutputName  # e.g. common-tf-state::TerraformStateBucketName
            dynamodb_table: StackName::OutputName  # e.g. common-tf-state::TerraformLockTableName


Backend SSM Parameters in r4y.yml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to the CloudFormation lookup, backend config options can be looked up
directly from SSM Parameters.

Either for a single module::

    ---
    deployments:
      - modules:
          - path: mytfmodule
            options:
              terraform_backend_config:
                region: us-east-1
                bucket: ${ssm ParamNameHere::region=us-east-1}
                dynamodb_table: ${ssm ParamNameHere::region=us-east-1}


and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: mytfmodule
          - path: anothermytfmodule
        module_options:  # shared between all modules in deployment
          terraform_backend_config:
            region: us-east-1
            bucket: ${ssm ParamNameHere::region=us-east-1}
            dynamodb_table: ${ssm ParamNameHere::region=us-east-1}


Part 4: Variable Values
-----------------------

Finally, define your per-environment variables using one or both of the following options.


Values in Variable Definitions Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standard Terraform `tfvars
<https://www.terraform.io/docs/configuration/variables.html#variable-definitions-tfvars-files>`_
files can be used, exactly as one normally would with ``terraform apply -var-file``.
Runway will automatically detect them when named like ``ENV-REGION.tfvars`` or ``ENV.tfvars``.

E.g. ``common-us-east-1.tfvars``::

    region = "us-east-1"
    image_id = "ami-abc123"


Values in r4y.yml
~~~~~~~~~~~~~~~~~~~~

Variable values can also be specified as parameter values in r4y.yml. It
is recommended to use `Lookups`_ in the ``parameters`` section to
assist in selecting the appropriate values for the deploy environment and/or
region being deployed to but, this is not a requirement if the value will
remain the same.

::

    ---

    deployments:
      - modules:
          - path: mytfmodule
            parameters:
              region: ${env AWS_REGION}
              image_id: ${var image_id.${env AWS_REGION}}
              mylist:
                - item1
                - item2
              mymap:
                key1: value1
                key2: value1

and/or
::

    ---

    deployments:
      - parameters:
          region: ${env AWS_REGION}
          image_id: ${var image_id.${env AWS_REGION}}
          mylist:
            - item1
            - item2
          mymap:
            key1: value1
            key2: value1
        modules:
          - mytfmodule
