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
-------------------------------------------------------

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
        module-options:  # shared between all modules in deployment
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
        module-options:  # shared between all modules in deployment
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
        module-options:  # shared between all modules in deployment
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
        module-options:  # shared between all modules in deployment
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

Disabling NPM CI
----------------
At the start of each module execution, Runway will execute ``npm ci`` to ensure
Serverless Framework is installed in the project (so Runway can execute it via
``npx sls``. This can be disabled (e.g. for use when the ``node_modules``
directory is pre-compiled) via the ``skip_npm_ci`` module option:
::

    ---
    deployments:
      - modules:
          - path: myslsproject.sls
            options:
              skip_npm_ci: true


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

Disabling NPM CI
----------------
At the start of each module execution, Runway will execute ``npm ci`` to ensure
the CDK is installed in the project (so Runway can execute it via
``npx cdk``. This can be disabled (e.g. for use when the ``node_modules``
directory is pre-compiled) via the ``skip_npm_ci`` module option:
::

    ---
    deployments:
      - modules:
          - path: mycdkproject.cdk
            options:
              skip_npm_ci: true


Kubernetes
===========
Kubernetes manifests can be deployed via Runway, offering an ideal way to
handle core infrastructure-layer (e.g. shared ConfigMaps & Service Accounts)
configuration of clusters. Perform the following steps to align your k8s
directories with Runway's requirements & best practices.

Part 1: Adding Kubernetes to Deployment
--------------------------------------
Start by adding your
`Kustomize overlay organized <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays>`_
Kubernetes directory to your runway.yml's list of modules.

Directory tree:
::

    .
    ├── runway.yml
    └── kubernetesstuff.k8s
        ├── base
        │   ├── kustomization.yaml
        │   └── service.yaml
        └── overlays
            ├── prod
            │   └── kustomization.yaml
            └── staging
                └── kustomization.yaml


runway.yml:
::

    ---
    deployments:
      - modules:
          - kubernetesstuff.k8s
        regions:
          - us-east-1

Each overlay's kustomization can be as simple as including the base directory
and (optionally) adding a resource prefix. E.g., in the staging directory's
kustomize.yml::

    bases:
      - ../base
    namePrefix: staging-

The base directory's kustomization then in turn includes the base directory's
manifests::

    resources:
      - service.yaml


Part 2: Specify the Kubectl Version
-------------------------------------
By specifying the version via a ``.kubectl-version`` file in your overlay
directory, or a module option, Runway will automatically download & use that
version for the module. This is recommended to keep a predictable experience
when deploying your module.

.kubectl-version::

    1.14.5


or in runway.yml, either for a single module::

    ---
    deployments:
      - modules:
          - path: myk8smodule
            options:
              kubectl_version:
                "*": 1.14.5  # applies to all environments
                # prod: 1.13.0  # can also be specified for a specific environment


and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: myk8smodule
          - path: anotherk8smodule
        module-options:  # shared between all modules in deployment
          kubectl_version:
            "*": 1.14.5  # applies to all environments
            # prod: 1.13.0  # can also be specified for a specific environment


Without a version specified, Runway will fallback to whatever ``kubectl``
it finds first in your PATH.

Part 3: Setting KUBECONFIG location
-------------------------------------
If using a non-default kubeconfig location, you can provide it using Runway's
option for setting environment variables. This can be set as a relative path
or an absolute one. E.g.::

    ---
    deployments:
      - modules:
          - path: myk8smodule
            options:
              kubectl_version:
      - regions:
          - us-east-1
    env-vars:
      staging:
        KUBECONFIG:
          - .kube
          - staging
          - config
      prod:
        KUBECONFIG:
          - .kube
          - prod
          - config

(this would set ``KUBECONFIG`` to ``<path_to_runway.yml>/.kube/staging/config``
in the staging environment)

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

Runway Plugin Support
=====================
Need to expand runway to wrap other tools? Yes - you can do that with Runway Plugin Support.

Overview
--------
Runway can import Python modules that can perform custom deployments with your
own set of Runway modules. Let's say for example you want to have Runway
execute an Ansible playbook to create an EC2 security group as one of the steps
in the middle of your runway deployment list - this is possible with your own
plugin. The Runway plugin support allows you to mix-and-match natively
supported modules (e.g. CloudFormation, Terraform) with plugins you write
providing additional support for non-native modules. Although written in
Python, these plugins can natively execute non Python binaries.

RunwayModule Class
------------------
Runway provides a Python Class named ``RunwayModule`` that can be imported
into your custom plugin/Python module. This base class will give you the
ability to write your own module that can be added to your runway.yml
deployment list (More info on runway.yml below). There are three required
functions::

- plan - This code block gets called when ``runway taxi`` executes
- deploy - This code block gets called when ``runway takeoff`` executes
- destroy - This code block gets called when ``runway destroy`` executes

All of these functions are required, but are permitted to be empty no-op/pass
statements if applicable.

Context Object
--------------
``self.context`` includes many helpful resources for use in your Python
module. Some notable examples are::

- self.context.env_name - name of the environment
- self.context.env_region - region in which the module is being executed
- self.context.env_vars - OS environment variables provided to the module
- self.path - path to your runway module folder

runway.yml Example
-------------------
After you have written your plugin, you need to add the module ``class_path``
to your module's configuration. Below is an example ``runway.yml`` containing a
single module that looks for an Ansible playbook in a folder at the root of
your Runway environment (i.e. repo) named "security_group.ansible".

Setting ``class_path`` tells runway to import the DeployToAWS Python class,
from a file named Ansible.py in a folder named "local_runway_extensions"
(Standard Python import conventions apply). Runway will execute the ``deploy``
function in your class when you perform a ``runway deploy`` (AKA takeoff).

::

    deployments:
      - modules:
          - path: security_group.ansible
            class_path: local_runway_extensions.Ansible.DeployToAWS
        regions:
          - us-east-1


Below is the ``Ansible.py`` module referenced above that wraps the
``ansible-playbook`` command. It will be responsible for deploying an EC2 Security Group from the playbook
with a naming convention of ``<env>-<region>.yaml`` within a fictional
``security_group.ansible`` runway module folder. In this example, the
``ansible-playbook`` binary would already have been installed prior to a runway
deploy, but this example does check to see if it is installed before execution
and logs an error if not. The Runway plugin will only execute
the ansible-playbook against a ``yaml`` file associated with the environment and set for the Runway
execution and region defined in the ``runway.yml``.

Using the above ``runway.yml`` and the plugin/playbook below saved to the Runway
module folder you will only have a deployment occur in the ``dev`` environment
in ``us-east-1``.  If you decide to perform a runway deployment in the ``prod``
environment, or in a different region, the ansible-playbook deployment will be
skipped. This matches the behavior of the Runway's native modules.

::

    """Ansible Plugin example for Runway."""

    import logging
    import subprocess
    import sys
    import os

    from runway.module import RunwayModule
    from runway.util import which

    LOGGER = logging.getLogger('runway')


    def check_for_playbook(playbook_path):
        """Determine if environment/region playbook exists."""
        if os.path.isfile(playbook_path):
            LOGGER.info("Processing playbook: %s", playbook_path)
            return {'skipped_configs': False}
        else:
            LOGGER.error("No playbook for this environment/region found -- "
                         "looking for %s", playbook_path)
            return {'skipped_configs': True}


    class DeployToAWS(RunwayModule):
        """Ansible Runway Module."""

        def plan(self):
            """Skip plan"""
            LOGGER.info('plan not currently supported for Ansible')
            pass

        def deploy(self):
            """Run ansible-playbook."""
            if not which('ansible-playbook'):
                LOGGER.error('"ansible-playbook" not found in path or is not '
                             'executable; please ensure it is installed'
                             'correctly.')
                sys.exit(1)
            playbook_path = (self.path + "-" + self.context.env_name + self.context.env_region)
            response = check_for_playbook(playbook_path)
            if response['skipped_configs']:
                return response
            else:
                subprocess.check_output(
                    ['ansible-playbook', playbook_path])
                return response

        def destroy(self):
            """Skip destroy."""
            LOGGER.info('Destroy not currently supported for Ansible')
            pass



And below is the example Ansible playbook itself, saved as
``dev-us-east-1.yaml`` in the security_group.ansible folder:

::

    - hosts: localhost
      connection: local
      gather_facts: false
      tasks:
          - name: create a security group in us-east-1
            ec2_group:
              name: dmz
              description: Dev example ec2 group
              region: us-east-1
              rules:
                - proto: tcp
                  from_port: 80
                  to_port: 80
                  cidr_ip: 0.0.0.0/0
            register: security_group


The above would be deployed if ``runway deploy`` was executed in the ``dev``
environment to ``us-east-1``.
