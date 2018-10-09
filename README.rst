Runway
======

What?
-----

A lightweight wrapper around linting (e.g. yamllint) & infrastructure
deployment tools (e.g. CloudFormation, Terraform, Serverless) to ease
management of per-environment configs & deployment.

Why?
----

Very simple configuration to:

-  Perform automatic linting/verification
-  Ensure deployments are only performed when an environment config is
   present
-  Define an IAM role to assume for each deployment
-  Wrangle Terraform backend/workspace configs w/ per-environment tfvars
-  Avoid long-term tool lock-in

   -  runway is a simple wrapper around standard tools. It simply helps
      to avoid convoluted Makefiles / CI jobs

How?
----

Complete quickstart documentation, including Docker images,
CloudFormation templates, and walkthrough can be found
`here <https://github.com/onicagroup/runway/blob/master/quickstarts/README.md>`__

Basic Concepts
~~~~~~~~~~~~~~

-  Modules:

   -  A single-tool configuration of an
      application/component/infrastructure (e.g. a set of CloudFormation
      stacks to deploy a VPC, a Serverless or CDK app)

-  Regions:

   -  AWS regions

-  Environments:

   -  A Serverless stage, a Terraform workspace, etc.
   -  Environments are determined automatically from:

      1. Git branches. We recommend promoting changes through clear
         environment branches (prefixed with ``ENV-``). For example,
         when running a deployment in the ``ENV-dev`` branch ``dev``
         will be the environment. The ``master`` branch can also be used
         as a special 'shared' environment called ``common`` (e.g. for
         modules not normally promoted through other environments).
      2. The parent folder name of each module. For teams with a
         preference or technical requirement to not use git branches,
         each environment can be represented on disk as a folder.
         Instead of promoting changes via git merges, changes can be
         promoted by copying the files between the environment folders.
         See the ``ignore_git_branch`` runway.yml config option.

         -  The folder name of the module itself (not its parent folder)
            if the ``ignore_git_branch`` and ``current_dir`` runway.yml
            config config options are both used (see "Directories as
            Environments with a Single Module" in "Repo Structure").

      3. The ``DEPLOY_ENVIRONMENT`` environment variable.

-  Deployments:

   -  Mappings of modules to regions, optionally with AWS IAM roles to
      assume

-  runway.yml:

   -  List of deployments
   -  When the ``CI`` environment variable is set, all deployments are
      run in order; otherwise, the user is prompted for deployments to
      run.

Repo Structure
~~~~~~~~~~~~~~

Git Branches as Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample repo structure, showing 2 modules using environment git branches
(these same files would be present in each environment branch, with
changes to any environment promoted through branches):

::

    .
    ├── myapp.cfn
    │   ├── dev-us-west-2.env
    │   ├── prod-us-west-2.env
    │   ├── myapp.yaml
    │   └── templates
    │       └── foo.json
    ├── myapp.tf
    │   ├── backend.tfvars
    │   ├── dev-us-east-1.tfvars
    │   ├── prod-us-east-1.tfvars
    │   └── main.tf
    └── runway.yml

Directories as Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Another sample repo structure, showing the same modules nested in
environment folders:

::

    .
    ├── dev
    │   ├── myapp.cfn
    │   │   ├── dev-us-west-2.env
    |   │   ├── prod-us-west-2.env
    │   │   ├── myapp.yaml
    │   │   └── templates
    │   │       └── myapp_cf_template.json
    │   ├── myapp.tf
    │   │   ├── backend.tfvars
    │   │   ├── dev-us-east-1.tfvars
    |   │   ├── prod-us-east-1.tfvars
    │   │   └── main.tf
    │   └── runway.yml
    └── prod
        ├── myapp.cfn
        │   ├── dev-us-west-2.env
        │   ├── prod-us-west-2.env
        │   ├── myapp.yaml
        │   └── templates
        │       └── myapp_cf_template.json
        ├── myapp.tf
        │   ├── backend.tfvars
        │   ├── dev-us-east-1.tfvars
        │   ├── prod-us-east-1.tfvars
        │   └── main.tf
        └── runway.yml

Directories as Environments with a Single Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Another sample repo structure, showing environment folders containing a
single CloudFormation module at their root (combining the
``current_dir`` & ``ignore_git_branch`` "Runway Config File" options to
merge the Environment & Module folders):

::

    .
    ├── dev
    │   ├── dev-us-west-2.env
    │   ├── prod-us-west-2.env
    │   ├── myapp.yaml
    │   ├── runway.yml
    │   └── templates
    │       └── myapp_cf_template.json
    └── prod
        ├── dev-us-west-2.env
        ├── prod-us-west-2.env
        ├── myapp.yaml
        ├── runway.yml
        └── templates
            └── myapp_cf_template.json

Runway Config File
~~~~~~~~~~~~~~~~~~

runway.yml example:

::

    ---
    # Order that modules will be deployed. A module will be skipped if a
    # corresponding env/config file is not present in its folder.
    # (e.g., for cfn modules, if a dev-us-west-2.env file is not in the 'app.cfn'
    # folder when running a dev deployment of 'app' to us-west-2 then it will be
    # skipped.)
    deployments:
      - modules:
          - myapp.cfn
        regions:
          - us-west-2
      - modules:
          - myapp.tf
        regions:
          - us-east-1
        assume-role:  # optional
          # When running multiple deployments, post_deploy_env_revert can be used
          # to revert the AWS credentials in the environment to their previous
          # values
          # post_deploy_env_revert: true
          dev: arn:aws:iam::account-id1:role/role-name
          prod: arn:aws:iam::account-id2:role/role-name
          # A single ARN can be specified instead, to apply to all environments
          # arn: arn:aws:iam::account-id:role/role-name
          # Role duration can be set at the top level, or in a specific environment
          # duration: 7200
          # dev:
          #   arn: arn:aws:iam::account-id1:role/role-name
          #   duration: 7200
        account-alias:  # optional
          # A mapping of environment -> alias mappings can be provided to have
          # Runway verify the current assumed role / credentials match the
          # necessary account
          dev: my_dev_account
          prod: my_dev_account
        account-id:  # optional
          # A mapping of environment -> id mappings can be provided to have Runway
          # verify the current assumed role / credentials match the necessary
          # account
          dev: 123456789012
          prod: 345678901234
        env_vars:  # optional environment variable overrides
          dev:
            AWS_PROFILE: foo
          prod:
            AWS_PROFILE: bar
          "*":  # Applied to all environments
            ANOTHER_VAR: foo
        skip-npm-ci: false  # optional, and should rarely be used. Omits npm ci
                            # execution during Serverless deployments
                            # (i.e. for use with pre-packaged node_modules)

    # If using environment folders instead of git branches, git branch lookup can
    # be disabled entirely (see "Repo Structure")
    # ignore_git_branch: true

runway.yml can also be placed in a module folder (e.g. a
repo/environment containing only one module doesn't need to nest the
module in a subfolder):

::

    ---
    # This will deploy the module in which runway.yml is located
    deployments:
      - current_dir: true
        regions:
          - us-west-2
        assume-role:
          arn: arn:aws:iam::account-id:role/role-name

    # If using environment folders instead of git branches, git branch lookup can
    # be disabled entirely (see "Repo Structure"). See "Directories as Environments
    # with a Single Module" in "Repo Structure".
    # ignore_git_branch: true

Installation
------------

-  Install Python

   -  On Linux (assuming default Bash shell; adjust for others
      appropriately):

      -  Setup your shell for user-installed (non-root) pip packages:

         -  ``echo 'export PATH=$HOME/.local/bin:$PATH' >> ${HOME}/.bashrc``
         -  ``source ${HOME}/.bashrc``

      -  Install Python/pip:

         -  Debian-family (e.g. Ubuntu):
            ``sudo apt-get -y install python-pip python-minimal``
         -  Amazon Linux should should work out of the box
         -  RHEL-family:

            -  If easy\_install is available:
               ``easy_install --user pip``
            -  Otherwise, enable EPEL and
               ``sudo yum install python-pip``

   -  On macOS (assuming default Bash shell; adjust for others
      appropriately):

      -  ``if ! which pip > /dev/null; then easy_install --user pip; fi``
      -  ``echo 'export PATH="${HOME}/Library/Python/2.7/bin:${PATH}"' >> ${HOME}/.bash_profile``
      -  ``source ${HOME}/.bash_profile``

   -  On Windows:

      -  This can be done via the Chocolately package manager (e.g.
         ``choco install python2``), or manually from their website

         -  If installing via Chocolately, default options will be
            sufficient. Close/reopen terminals after installation to use
            the updated PATH
         -  If installing manually, use the default options with the
            exception of the "Add python to Path" (it should be
            enabled).

      -  Add ``%USERPROFILE%\AppData\Roaming\Python\Scripts`` to PATH
         environment variable

-  Install runway (doesn't require sudo/admin permissions):

   -  ``pip install --user runway``

      -  If this produces an error like
         ``Unknown distribution option: 'python_requires'``, upgrade
         setuptools first ``pip install --user --upgrade setuptools``

Use
---

-  ``runway test`` (aka ``runway preflight``) - execute this in your
   environment to catch errors; if it exits ``0``, you're ready for...
-  ``runway plan`` (aka ``runway taxi``) - this optional step will show
   the diff/plan of what will be changed. With a satisfactory plan you
   can...
-  ``runway deploy`` (aka ``runway takeoff``) - if running
   interactively, you can choose which deployment to run; otherwise
   (i.e. on your CI system) each deployment will be run in sequence.

Removing Deployments
~~~~~~~~~~~~~~~~~~~~

-  ``runway destroy`` (aka ``runway dismantle``) - if running
   interactively, you can choose which deployment to remove; otherwise
   (i.e. on your CI system) every deployment will be run in reverse
   sequence (use with caution).

Module Configurations
---------------------

CloudFormation
~~~~~~~~~~~~~~

CloudFormation modules are managed by 2 files: a key/value environment
file, and a yaml file defining the stacks/templates/params.

Environment - name these in the form of ENV-REGION.env (e.g.
dev-us-east-1.env) or ENV.env (e.g. dev.env):

::

    # Namespace is used as each stack's prefix
    # We recommend an (org/customer)/environment delineation
    namespace: contoso-dev
    environment: dev
    customer: contoso
    region: us-west-2
    # The stacker bucket is the S3 bucket (automatically created) where templates
    # are uploaded for deployment (a CloudFormation requirement for large templates)
    stacker_bucket_name: stacker-contoso-us-west-2

Stack config - these can have any name ending in .yaml (they will be
evaluated in alphabetical order):

::

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

The config yaml supports many more features; see the full Stacker
documentation for more detail (e.g. `stack configuration
options <http://stacker.readthedocs.io/en/latest/config.html#stacks>`__,
`additional
lookups <http://stacker.readthedocs.io/en/latest/lookups.html>`__ in
addition to output (e.g. SSM, DynamoDB))

Environment Values Via Runway Deployment/Module Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition or in place of the environment file(s), environment values
can be provided via deployment and module options.

Top-level Runway Config
'''''''''''''''''''''''

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
'''''''''''''''''''

::

    ---
    environments:
      dev:
        namespace: contoso-dev
        foo: bar

(in ``runway.module.yaml``)

Serverless
~~~~~~~~~~

Standard `Serverless <https://serverless.com/framework/>`__ rules apply,
with the following recommendations/caveats:

-  Runway environments map directly to Serverless stages.
-  A ``package.json`` file is required, specifying the serverless
   dependency, e.g.:

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

-  We strongly recommend you commit the package-lock.json that is
   generated after running ``npm install``
-  Each stage requires either its own variables file (even if empty for
   a particular stage) in one of the following forms, or a configured
   environment in the module options (see
   ``Specifying Environments Via Runway Module Options`` below):

   ::

       env/STAGE-REGION.yml
       config-STAGE-REGION.yml
       env/STAGE.yml
       config-STAGE.yml
       env/STAGE-REGION.json
       config-STAGE-REGION.json
       env/STAGE.json
       config-STAGE.json

Specifying Environments Via Runway Deployment/Module Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environments can be specified via deployment and module options in lieu
of variable files.

Top-level Runway Config
'''''''''''''''''''''''

::

    ---

    deployments:
      - modules:
          - path: myslsmodule
            environments:
              dev: true
              prod: true

and/or:

::

    ---

    deployments:
      - environments:
          dev: true
          prod: true
        modules:
          - myslsmodule

In Module Directory
'''''''''''''''''''

::

    ---
    environments:
      dev: true
      prod: true

(in ``runway.module.yaml``)

Terraform
~~~~~~~~~

Standard Terraform rules apply, with the following
recommendations/caveats:

-  Each environment requires its own tfvars file, in the form of
   ENV-REGION.tfvars (e.g. dev-contoso.tfvars).
-  We recommend (but do not require) having a backend configuration
   separate from the terraform module code:

main.tf:

::

    terraform {
      backend "s3" {
        key = "some_unique_identifier_for_my_module" # e.g. contosovpc
      }
    }
    # continue with code here...

backend-REGION.tfvars, or backend-ENV-REGION.tfvars, or
backend-ENV.tfvars (e.g. backend-us-east-1.tfvars):

::

    bucket = "SOMEBUCKNAME"
    region = "SOMEREGION"
    dynamodb_table = "SOMETABLENAME"

tfenv
^^^^^

If a ``.terraform-version`` file is placed in the module,
`tfenv <https://github.com/kamatama41/tfenv>`__ will be invoked to
ensure the appropriate version is installed prior to module deployment.

Environment Values Via Runway Deployment/Module Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition or in place of the variable file(s), variable values can be
provided via deployment and module options.

Top-level Runway Config
'''''''''''''''''''''''

::

    ---

    deployments:
      - modules:
          - path: mytfmodule
            environments:
              dev:
                foo: bar

and/or

::

    ---

    deployments:
      - environments:
          dev:
            foo: bar
        modules:
          - mytfmodule

In Module Directory
'''''''''''''''''''

::

    ---
    environments:
      dev:
        namespace: contoso-dev
        foo: bar

(in ``runway.module.yaml``)

CDK
~~~

Standard `AWS CDK <https://awslabs.github.io/aws-cdk/>`__ rules apply,
with the following recommendations/caveats:

-  A ``package.json`` file is required, specifying the aws-cdk
   dependency. E.g.:

   ::

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

-  We strongly recommend you commit the package-lock.json that is
   generated after running ``npm install``

Build Steps
^^^^^^^^^^^

Build steps (e.g. for compiling TypeScript) can be specified in the
module options. These steps will be run before each diff, deploy, or
destroy.

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
^^^^^^^^^^^^^^^^^^^

Environments can be specified via deployment and/or module options. Each
example below shows the explicit CDK ``ACCOUNT/REGION`` environment
mapping; these can be alternately be specified with a simple boolean
(e.g. ``dev: true``).

Top-level Runway Config
'''''''''''''''''''''''

::

    ---

    deployments:
      - modules:
          - path: mycdkmodule
            environments:
              dev: 987654321098/us-west-2
              prod: 123456789012/us-west-2

and/or:

::

    ---

    deployments:
      - environments:
          dev: 987654321098/us-west-2
          prod: 123456789012/us-west-2
        modules:
          - mycdkmodule

In Module Directory
'''''''''''''''''''

::

    ---
    environments:
      dev: 987654321098/us-west-2
      prod: 123456789012/us-west-2

(in ``runway.module.yaml``)

Additional Functionality
------------------------

whichenv
~~~~~~~~

Execute ``runway whichenv`` to output the name of the currently detected
environment (see ``Basic Concepts`` for an overview of how runway
determines the environment name).

Static Website Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~

Runway comes pre-packaged with a module plugin for performing idempotent
deployments of static websites. It combines CloudFormation stacks (for
S3 buckets & CloudFront Distribution) with additional logic to build &
sync the sites.

It can be used with a configuration like the following:

::

    deployments:
      - modules:
          - path: web
            class_path: runway.module.staticsite.StaticSite
            environments:
              dev:
                namespace: contoso-dev
                staticsite_acmcert_arn: arn:aws:acm:us-east-1:123456789012:certificate/...
            options:
              build_steps:
                - npm ci
                - npm run build
              build_output: dist
        regions:
          - us-west-2

This will build the website in ``web`` via the specified build\_steps
and then upload the contents of ``web/dist`` to a S3 bucket created in
the CloudFormation stack ``web-dev-conduit``. On subsequent deploys, the
website will be built and synced only if the (non-git-ignored) files in
``web`` change.

The site domain name is available via the ``CFDistributionDomainName``
output of the ``<namespace>-<path>`` stack (e.g. ``contoso-dev-web``
above) and will be displayed on stack creation/updates.

See additional options
`here <https://github.com/onicagroup/runway/blob/master/docs/staticsite.md>`__,
or a start-to-finish example walkthrough
`here <https://github.com/onicagroup/runway/blob/master/quickstarts/conduit/README.md>`__.

gen-sample
~~~~~~~~~~

Execute ``runway gen-sample`` followed by a module type to create a
sample module directory, containing example files appropriate for the
module type: \* ``runway gen-sample cfn``: Creates a sample
CloudFormation module in ``sampleapp.cfn`` \* ``runway gen-sample sls``:
Creates a sample Serverless Framework module in ``sampleapp.sls`` \*
``runway gen-sample stacker``: Creates a sample CloudFormation module
(with Python templates using Troposphere and awacs) in
``runway-sample-tfstate.cfn`` \* ``runway gen-sample tf``: Creates a
sample Terraform module in ``sampleapp.tf``
