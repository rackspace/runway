.. _AWS CDK: https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html
.. _CloudFormation: https://aws.amazon.com/cloudformation/
.. _Serverless Framework: https://serverless.com/
.. _Stacker: https://stacker.readthedocs.io/en/stable/
.. _Terraform: https://www.terraform.io
.. _Troposphere: https://github.com/cloudtools/troposphere

.. _runway-config-options:

Runway Config File
==================

Top-Level Configuration
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: runway.config.Config

.. _runway-deployment:

Deployment
^^^^^^^^^^

.. autoclass:: runway.config.DeploymentDefinition

.. _runway-module:

Module
^^^^^^

.. autoclass:: runway.config.ModuleDefinition

.. _runway-test:

Test
^^^^

.. autoclass:: runway.config.TestDefinition

Sample
^^^^^^

.. code-block:: yaml

    ---
    # Order that tests will be run. Test execution is triggered with the
    # 'runway test' command. Testing will fail and exit if any of the
    # individual tests fail unless they are marked with 'required: false'.
    # Please see the doc section dedicated to tests for more details.

    tests:
      - name: test-names-are-optional
        type: script  # there are a few built in test types
        args:  # each test has their own set of arguments they can accept
          commands:
            - echo "Beginning a test..."
            - cd app.sls && npm test && cd ..
            - echo "Test complete!"
      - name: unimportant-test
        type: cfn-lint
        required: false  # tests will still pass if this fails
      - type: yamllint  # not all tests accept arguments

    # Order that modules will be deployed. A module will be skipped if a
    # corresponding env/config is not present (either in a file in its folder
    # or via an environments option specified here on the deployment or
    # module)
    # E.g., for cfn modules, if
    # 1) a dev-us-west-2.env file is not in the 'app.cfn' folder when running
    #    a dev deployment of 'app' to us-west-2,
    # and
    # 2) dev is not specified under the deployment or module's environments
    #
    # then it will be skipped.

    deployments:
      - modules:
          - myapp.cfn
        regions:
          - us-west-2

      - name: terraformapp  # deployments can optionally have names
        modules:
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

        # Environment options (e.g. values for CFN .env file, TF .tfvars) can
        # be provided at the deployment level -- the options will be applied to
        # every module in the environment
        environments:
          dev:
            region: us-east-1
            image_id: ami-abc123

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

        # env_vars set OS environment variables for the module (not logical
        # environment values like those in a CFN .env or TF .tfvars file).
        # They should generally not be used (they are provided for use with
        # tools that absolutely require it, like Terraform's
        # TF_PLUGIN_CACHE_DIR option)
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

      # Start of another deployment
      - modules:
          - path: myapp.cfn
            # Environment options (e.g. values for CFN .env file, TF .tfvars) can
            # be provided for a single module (replacing or supplementing the
            # use of environment/tfvars/etc files in the module)
            environments:
              dev:
                region: us-east-1
                image_id: ami-abc123
            tags:  # Modules can optionally have tags.
              # This is a list of strings that can be "targeted"
              # by passing arguments to the deploy/destroy command.
              - some-string
              - app:example
              - tier:web
              - owner:onica
              # example: `runway deploy --tag app:example --tag tier:web`
              #   This would select any modules with BOTH app:example AND tier:web
        regions:
          - us-west-2

    # If using environment folders instead of git branches, git branch lookup can
    # be disabled entirely (see "Repo Structure")
    # ignore_git_branch: true

The runway config file can also be placed in a module folder
(e.g. a repo/environment containing only one module doesn't need to nest the module in a subfolder)

.. code-block:: yaml

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
