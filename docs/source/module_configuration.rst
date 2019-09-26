.. _module-configurations:

=====================
Module Configurations
=====================

CloudFormation
==============
CloudFormation modules are managed by 2 files:

- a key/value environment file
- a yaml file defining the stacks/templates/params.

Environment - name these in the form of ENV-REGION.env (e.g. dev-us-east-1.env) or ENV.env (e.g. dev.env)::

    # Namespace is used as each stack's prefix
    # We recommend an (org/customer)/environment delineation
    namespace: contoso-dev
    environment: dev
    customer: contoso
    region: us-west-2
    # The stacker bucket is the S3 bucket (automatically created) where templates
    # are uploaded for deployment (a CloudFormation requirement for large templates)
    stacker_bucket_name: stacker-contoso-us-west-2

Stack config - these can have any name ending in .yaml (they will be evaluated in alphabetical order)::

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

The config yaml supports many more features; see the full Stacker documentation for more detail
(e.g. stack configuration options, additional lookups in addition to output (e.g. SSM, DynamoDB))

Environment Values Via Runway Deployment/Module Options
---------------------------------------------------------

In addition or in place of the environment file(s), environment values can be provided via deployment and module options.

Top-level Runway Config
~~~~~~~~~~~~~~~~~~~~~~~
::

    ---

    deployments:
      - modules:
          - path: mycfnstacks
            environments:
              dev:
                namespace: contoso-dev
                foo: bar

and/or

::

    ---

    deployments:
      - environments:
          dev:
            namespace: contoso-dev
            foo: bar
        modules:
          - mycfnstacks

In Module Directory
~~~~~~~~~~~~~~~~~~~
::

    ---
    environments:
      dev:
        namespace: contoso-dev
        foo: bar

(in ``runway.module.yml``)

Terraform
=========
Runway provides a simple way to run the Terraform versions you want with
variable values specific to each environment. Perform the following steps to
align your Terraform directory with Runway's requirements & best practices.

Part 1: Adding Terraform to Deployment
--------------------------------------
Start by adding your Terraform directory to your runway.yml's list of modules.

(Note: to Runway, a module is just a directory in which to run
``terraform apply``, ``serverless deploy``, etc - no relation to Terraform's
concept of modules)

Directory tree:
::

    .
    ├── runway.yml
    └── terraformstuff.tf
        └── main.tf


runway.yml:
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


or in runway.yml, either for a single module::

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

Backend Config in runway.yml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Backend config options can also be specified as a module option in runway.yml:

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

Backend CloudFormation Outputs in runway.yml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A recommended option for managing the state bucket and table is to create
them via CloudFormation (try running ``runway gen-sample cfn`` to get a
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
                dynamodb_table: StackName::OutputName  # e.g. common-tf-state::TerraformLockTableName


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

Backend SSM Parameters in runway.yml
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
              terraform_backend_ssm_params:
                bucket: ParamNameHere
                dynamodb_table: ParamNameHere


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
          terraform_backend_ssm_params:
            bucket: ParamNameHere
            dynamodb_table: ParamNameHere


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


Values in runway.yml
~~~~~~~~~~~~~~~~~~~~
Variable values can also be specified as environment values (no relation to
OS environment variables, just values for the Runway logical environment) in
runway.yml::

    ---

    deployments:
      - modules:
          - path: mytfmodule
            environments:
              dev:
                region: us-east-1
                image_id: ami-abc123

and/or
::

    ---

    deployments:
      - environments:
          dev:
            region: us-east-1
            image_id: ami-abc123
        modules:
          - mytfmodule


Serverless
==========
Standard `Serverless
<https://serverless.com/framework/>`_ rules apply, with the following
recommendations/caveats:

- Runway environments map directly to Serverless stages.
- A ``package.json`` file is required, specifying the serverless dependency, e.g.:

::

    {
      "name": "mymodulename",
      "version": "1.0.0",
      "description": "My serverless module",
      "main": "handler.py",
      "devDependencies": {
        "serverless": "^1.25.0"
      },
      "author": "Serverless Devs",
      "license": "ISC"
    }

- We strongly recommend you commit the package-lock.json that is generated
  after running ``npm install``
- Each stage requires either its own variables file (even if empty for a
  particular stage) in one of the following forms, or a configured environment
  in the module options (see ``Enabling Environments Via Runway
  Deployment/Module Options`` below):

- ``env/STAGE-REGION.yml``
- ``config-STAGE-REGION.yml``
- ``env/STAGE.yml``
- ``config-STAGE.yml``
- ``env/STAGE-REGION.json``
- ``config-STAGE-REGION.json``
- ``env/STAGE.json``
- ``config-STAGE.json``


Enabling Environments Via Runway Deployment/Module Options
----------------------------------------------------------
Environments can be specified via deployment and module options in lieu of
variable files.

Top-level Runway Config
~~~~~~~~~~~~~~~~~~~~~~~
::

    ---

    deployments:
      - modules:
          - path: myslsmodule
            environments:
              dev: true
              prod: true

and/or
::

    ---

    deployments:
      - environments:
          dev: true
          prod: true
        modules:
          - myslsmodule

In Module Directory
~~~~~~~~~~~~~~~~~~~
::

    ---
    environments:
      dev: true
      prod: true

(in ``runway.module.yml``)

CDK
===
Standard `AWS CDK
<https://awslabs.github.io/aws-cdk/>`_ rules apply, with the following recommendations/caveats:

A ``package.json`` file is required, specifying the aws-cdk dependency. E.g.::

    {
      "name": "mymodulename",
      "version": "1.0.0",
      "description": "My CDK module",
      "main": "index.js",
      "dependencies": {
        "@aws-cdk/cdk": "^0.9.2",
        "@types/node": "^10.10.1"
      },
      "devDependencies": {
        "aws-cdk": "^0.9.2",
        "typescript": "^3.0.3"
      }
      "author": "My Org",
      "license": "Apache-2.0"
    }

We strongly recommend you commit the package-lock.json that is generated after running ``npm install``

Build Steps
-----------
Build steps (e.g. for compiling TypeScript) can be specified in the module options. These steps will be run before each diff, deploy, or destroy.
::

    deployments:
      - modules:
          - path: mycdkmodule
            environments:
              dev: true
            options:
              build_steps:
                - npx tsc

Environment Configs
-------------------
Environments can be specified via deployment and/or module options. Each example below shows the explicit CDK ``ACCOUNT/REGION`` environment mapping;
these can be alternately be specified with a simple boolean (e.g. ``dev: true``).

Top-level Runway Config
~~~~~~~~~~~~~~~~~~~~~~~
::

    ---

    deployments:
      - modules:
          - path: mycdkmodule
            environments:
              # CDK environment values can be specified in 3 forms:
              # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
              # dev:
              #   route_53_zone_id: Z3P5QSUBK4POTI
              # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
              # dev: 987654321098/us-west-2
              # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
              # dev: true

and/or:
::

    ---

    deployments:
      - environments:
          # CDK environment values can be specified in 3 forms:
          # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
          # dev:
          #   route_53_zone_id: Z3P5QSUBK4POTI
          # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
          # dev: 987654321098/us-west-2
          # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
          # dev: true
        modules:
          - mycdkmodule

In Module Directory
~~~~~~~~~~~~~~~~~~~
::

    ---
    environments:
      # CDK environment values can be specified in 3 forms:
      # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
      # dev:
      #   route_53_zone_id: Z3P5QSUBK4POTI
      # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
      # dev: 987654321098/us-west-2
      # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
      # dev: true

(in ``runway.module.yml``)

Static Site
===========

This module type performs idempotent deployments of static websites. It
combines CloudFormation stacks (for S3 buckets & CloudFront Distribution) with
additional logic to build & sync the sites.

It can be used with a configuration like the following::

    deployments:
      - modules:
          - path: web
            class_path: runway.module.staticsite.StaticSite
            environments:
              dev:
                namespace: contoso-dev
                staticsite_aliases: web.example.com,foo.web.example.com
                staticsite_acmcert_arn: arn:aws:acm:us-east-1:123456789012:certificate/...
            options:
              build_steps:
                - npm ci
                - npm run build
              build_output: dist
        regions:
          - us-west-2

This will build the website in ``web`` via the specified build_steps and then upload the contents of ``web/dist``
to an S3 bucket created in the CloudFormation stack ``web-dev-conduit``. On subsequent deploys, the website will
be built and synced only if the non-git-ignored files in ``web`` change.

The site domain name is available via the ``CFDistributionDomainName`` output of the ``<namespace>-<path>`` stack
(e.g. ``contoso-dev-web`` above) and will be displayed on stack creation/updates.

A number of `additional options are available <staticsite_config.html>`_. A start-to-finish example walkthrough
is available `in the Conduit quickstart <quickstart.html#conduit-serverless-cloudfront>`_.
