.. _runway-config-options:

Runway Config File
==================

The Basics
^^^^^^^^^^

At its simplest, a Runway project consists of a single module folder (for a Serverless application, say) and
a ``runway.yml`` at the same level::

    .
    ├── myapp.sls
    │   ├── serverless.yaml
    │   └── ...
    └── runway.yml


The ``runway.yml`` configuration file then consists of one "deployment" which contains just the one module which is deployable to just one region::

    ---
    deployments:
      - modules:
          - myapp.sls
        regions:
          - us-west-2

You can specify as many module folders and regions as you like, where each module *may* be deployed into each region::

    ---
    deployments:
      - modules:
          - database.cfn
          - path: myapp.sls
        regions:
          - us-east-1
          - us-east-2
          - us-west-1

*(Note that stating just the module folder name on its own is equivalent to explicitly specifying the folder name as the ``path``.)*

In this case, Runway *may* deploy the Cloudformation and Serverless modules each into one, two, or all three regions --
or even into none of them.  The particular combinations of modules and regions will depend on the configurations provided for
each module, but the regions here the only allowable ones.


Within a specific module, the associated deployment tool (e.g. Serverless or Terraform) will manage the order
that resources are created (or deleted), ensuring that dependencies are created earlier (or deleted later).
Resources might even be created or deleted in parallel, if the deployment tool determines there are no dependencies
between them.

Within a deployment, however, modules will be processed in the order specified in ``runway.yml``; so in this example,
the Stacker module ``database.cfn`` will be deployed before the Serverless module ``myapp.sls``.  Or, when
destroying the deployment, ``myapp.sls`` will be destroyed before ``database.cfn``.  Runway does not
attempt to determine the order itself based on dependencies between the modules.  **((VERIFY!!))**


Multiple Deployments
^^^^^^^^^^^^^^^^^^^^

The example above could be broken into two separate deployments within the same ``runway.yml`` file::

    ---
    deployments:
      - modules:
          - database.cfn
        regions:
          - us-east-2

      - modules:
          - myapp.sls
        regions:
          - us-east-1
          - us-east-2
          - us-west-1

Here we are stating that the Cloudformation stacks may be deployed to ``us-east-2`` only, while the Serverless
application may be deployed to three US regions.

When there are multiple deployments, they are created in the order they are listed in ``runway.yml``
(or destroyed in reverse order).  Runway does not attempt to determine the order itself based on
dependencies between the deployments.

Whether to use one deployment or many is currently mostly a stylistic choice.
Typically, modules that are tightly coupled should be in the same deployment, so in this particular
example the earlier single deployment would be preferred.


Environments
^^^^^^^^^^^^
An environment is a string name and a set of configuration values (buckets, ARNs, hostnames, etc)
for a particular instance of a Runway project.

An environment name should be descriptive but short, as it is usually used as part of the name of
each deployed resource.  It must start with a letter, and may consist of letters, digits, dashes and
underscores.

Environment names must also be unique within a given Runway project.

Most of the configuration values for an environment are specific to the various tools used to
deploy the various modules.  However, there are some configurations that are common to all of them


Environment Configuration in `runway.yml`
-----------------------------------------

Once you have a name for your environment, you can specify its setting directly in the main ``runway.yml``
file.

For example, say the one thing that differs between your QA and production environments is the S3 bucket they use::

    ---
    deployments:
        - modules:
            - path: myapp.sls
              environments:
                qa:
                   data_bucket: qa-data
                prod:
                   data_bucket: prod-data
                '*':
                   email_contact: foo@bar.com

Using the special environment name `'*'` as above, you can also specify values that apply to all
environments this module is deployed to.

If you have multiple modules that share values, you can specify them in each::

            - path: myapp1.sls
              environments:
                qa:
                   data_bucket: qa-data
                prod:
                   data_bucket: prod-data
                '*':
                   email_contact: foo@bar.com
            - path: myapp2.sls
              environments:
                qa:
                   data_bucket: qa-data
                prod:
                   data_bucket: prod-data
                '*':
                   email_contact: foo@bar.com

Or you can provide the values at the deployment level.  Or even at both levels::

    ---
    deployments:
        - modules:
            - path: myapp1.sls
              environments:
                qa:
                   data_bucket: qa-data-1
            - path: myapp2.sls
              environments:
                qa:
                   data_bucket: qa-data-2
          environments:
            prod:
               data_bucket: prod-data
            '*':
               email_contact: foo@bar.com

Here both applications will use the same bucket for production, and different buckets for QA.

This can be a bit confusing, especially in longer ``runway.yml`` files, and it also does not allow
you to have different values in different regions for the same environment.  As well, as the number
of environments grows (you might have one environment for every developer and for every QA), this
file will grow, and the risk of breaking things accidentally becomes a problem.

So a better approach would be to use a separate file for each environment and region.



Separate Environment Configuration Files
----------------------------------------

For a given module, configuration files in a module sub-folder called ``env`` *(recommended)* or in the module
folder itself *(deprecated)*.::

   .
    ├── mymod.cfn
    │   ├── env
    │   │   ├── qa-us-west-2.env
    │   │   └── prod-us-east-1.env
    │   └── ...
    └── runway.yml

For each environment, and for each region that particular environment should be deployed to, create a
file there called ``{env}-{region}.{extension}``, even if the file is empty

(Each type of module has its own particular file format and file extensions (e.g. ``.tfvars`` for Terraform, ``.env`` for
Stacker, and ``.yml`` for Serverless) for configuration, but they all use the same naming conventions.)

So in the above example, a Stacker module, we can deploy the ``qa`` environment to us-west-2 using the settings in that
file, while production would be deployed to us-east-1, using the settings in that file.

Further, for values that are common across regions, files named ``{env}.{extension}``, where values in these files
can be overridden by values in the corresponding ``{env}-{region}.{extension}`` files.::

   .
    ├── mymod.cfn
    │   ├── env
    │   │   ├── qa.env
    │   │   ├── qa-us-west-1.env
    │   │   ├── qa-us-west-2.env
    │   │   ├── prod.env
    │   │   └── prod-us-east-1.env
    │   └── ...
    └── runway.yml

One benefit is it's now easier and more clean for individuals to create their own environment:  just copy the appropriate file::

    env
    ├── dev-alice-us-west-2.tfvars
    ├── dev-bob-us-west-2.tfvars
    ├── dev-fred-us-west-1.tfvars
    ├── qa-susan-us-west-2.tfvars
    └── ...


Environment Variables
---------------------
In a handful of situations the only way to pass a setting to the deployment tools is via
operating system environment variables.

Each module will receive a copy of the OS environment variables active when Runway is executed.

Additional environment variables may be specified in the ``runway.yml`` file by adding an ``env_var`` node to a given
deployment node. Thus they are specific to each deployment, and not shared between them.

Under ``env_vars`` create a node using the name of the environment, or using ``'*'`` (with the quotes) if the values should
applicable to all environments::

    ---
    deployments:
        - modules:
            ...
        - regions:
            ...
        - env_vars:
            dev:
                AWS_PROFILE: foo
                LOG_LEVEL: info
            prod:
                AWS_PROFILE: bar
            '*':
                LOG_LEVEL: warn

This should be used sparingly.


Multiple Accounts
^^^^^^^^^^^^^^^^^

Restricting Deployments
-----------------------

You may optionally choose to restrict which account a given environment may be deployed to by adding
either an ``account-alias`` or ``account-id`` node to a deployment::

    ---
    deployments:
        - modules:
            ...
        - regions:
            ...
        - account-alias:
            qa: myaccount
        - account-id:
            prod: 123456789

In this example, Runway will attempt to deploy the environment ``qa`` only to the AWS account that
has the `alias <https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html>`_ ``myaccount``,
while Runway will deploy ``prod`` only to account ``123456789``.

Runway will not restrict any other environments.


Deploying Across Accounts
-------------------------

If your IAM permissions dictate that a particular deployment can be done only by assuming an IAM Role,
this can be configured by adding ``account-role`` to a deployment, specifying a role for
any environment that requires it::

    ---
    deployments:
        - modules:
            ...
        - regions:
            ...
        - account-role:
            qa: arn:aws:iam::123456789:role/role-name1
            prod:
                arn: arn:aws:iam::987654321:role/role-name2
                duration: 300
            post_deploy_env_revert: true
            duration: 600

With this configuration, Runway will attempt to assume ``role-name1`` when deploying the ``qa`` environment, and ask
to assume it for at most 10 minutes (600 seconds).  For ``prod`` it will attempt to assume ``role-name2`` for only
five minutes.

In both cases, immediately upon finishing the deployment Runway will explicitly un-assume the role and return to the existing AWS profile.
If ``post_deploy_env_revert`` is false, or not specified, Runway will not unassume the role explicitly

Note the two ways to specify an environment's role and duration.



Larger Example
^^^^^^^^^^^^^^

runway.yml sample::

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
            APP_PATH:  # When specified as list, will be treated as components of a path on disk
              - myapp.tf
              - foo
          prod:
            AWS_PROFILE: bar
            APP_PATH:
              - myapp.tf
              - foo
          "*":  # Applied to all environments
            ANOTHER_VAR: foo
        skip-npm-ci: false  # optional, and should rarely be used. Omits npm ci
                            # execution during Serverless deployments
                            # (i.e. for use with pre-packaged node_modules)
    
    # If using environment folders instead of git branches, git branch lookup can
    # be disabled entirely (see "Repo Structure")
    # ignore_git_branch: true

runway.yml can also be placed in a module folder (e.g. a repo/environment containing 
only one module doesn't need to nest the module in a subfolder)::

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
