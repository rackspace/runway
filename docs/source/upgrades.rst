.. _upgrades:

########
Upgrades
########

During a Runway upgrade (especially coming from a :code:`0.x` version) you may required to make changes to your configuration or modules. This page will describe common issues when upgrading and how to resolve them.



*******************************
Updating the Runway Config File
*******************************

You may need to update your Runway config file structure depending on how old of a Runway version you are upgrading from. Some config keys have changed in spelling, may make use of :code:`_` instead of :code:`-`, or have different functionality altogether. For example, compare this old config file:

.. code-block:: yaml

  deployments:
    - modules:
        - module-1.cfn
        - module-2.cfn
        - module-3.cfn
      regions:
        - us-east-1
      account-id:
        prod: 123412341234
      assume-role:
        post_deploy_env_revert: true
        prod: arn:aws:iam::123412341234:role/my-deployment-role
      environments:
        prod:
          namespace: my-account
          environment: prod

To this newer version:

.. code-block:: yaml

  variables:
    account_id:
      prod: 123412341234
    assume_role:
      prod: arn:aws:iam::123412341234:role/my-deployment-role
    parameters:
      prod:
        namespace: my-account
        environment: prod

  deployments:
    - modules:
        - module-1.cfn
        - module-2.cfn
        - module-3.cfn
      regions:
        - us-east-1
      account_id: ${var account_id.${env DEPLOY_ENVIRONMENT}}
      assume_role:
        arn: ${var assume_role.${env DEPLOY_ENVIRONMENT}}
        post_deploy_env_revert: true
      environments:
        prod: true
      parameters: ${var parameters.${env DEPLOY_ENVIRONMENT}}

In the above example, we've taken advantage of Runway's :code:`variables` key and we dynamically reference it based on our :code:`DEPLOY_ENVIRONMENT`. We also updated :code:`account-id` and :code:`assume-role` to :code:`account_id` and :code:`assume_role`.

Runway is very flexible about how you can structure your config, the above is only an example of one way to adjust it. Just keep in mind while upgrading that if you receive errors as soon as you start a :code:`runway` command, it is likely due to a config file error or no longer supported directive.

********************************
Migration from Stacker to CFNgin
********************************

Older versions of Runway used Stacker, which was then forked and included into the Runway project as CFNgin. This causes a few concerns while migrating older deployments.

------------------------------
Update References to Stacker
------------------------------

See :doc:`cfngin/migrating` for info on converting your older Stacker modules into CFNgin compatible versions.

-------------------------------
Migration of Stacker Blueprints
-------------------------------

In some environments, you may see usage of Stacker "Blueprints". These are Python scripts leveraging Troposphere to generate CloudFormation templates programmatically. While these can be incredibly powerful, they also come with a Python experience dependency and are prone to breaking due to AWS or Runway changes. In older deployments if the blueprint contains references to :code:`stacker` it will also need to be updated to use the new :code:`cfngin` library after a Runway upgrade, as described in :doc:`cfngin/migrating`.

In most cases it is easiest to:

1. Navigate to the AWS CloudFormation Console,
2. find the stack that was deployed using the blueprint,
3. copy its CloudFormation template data (optionally converting it to YAML on the way); and,
4. convert the deployment in Runway to use that static template so you can eliminate the blueprint.

This process leaves you with a much more simple to manage static template.

------------------------------------
A Note on Tagging in Stacker Modules
------------------------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
stacker_namespace / cfngin_namespace tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a Stacker/CFNgin deployment doesn't have a :code:`tags` key defined, a default value is used:

Stacker::

    stacker_namespace: ${namespace}

CFNgin::

    cfngin_namespace: ${namespace}

Because of this if you are upgrading a Stacker module without the :code:`tags` key defined, you'll see Runway attempting to adjust the tags on every resource in the module. This is because it is updating the default :code:`stacker_namespace` tag to a :code:`cfngin_namespace` tag. If you'd like to prevent this behavior, you can add a :code:`tags` key as follows::

    tags:
      stacker_namespace: ${namespace}

The above usage will cause CFNgin to keep the old :code:`stacker_namespace` tag with its original value, eliminating the need for changes to tags on resources.

^^^^^^^^^^^^^^^^^^^^
Int to String Errors
^^^^^^^^^^^^^^^^^^^^

When defining a :code:`tags` key directly onto a CFNgin stack definition (not the top level :code:`tags` key in the CFNgin config file), you may see an error regarding using an :code:`int` instead of a :code:`string`. For instance:

.. code-block:: yaml

  # This may return a "must be of type string" error
  my-stack-definition:
    template_path: ./my-templates/my-cloudformation-template.yaml
    tags:
      CostCenter: 1234

This can be resolved by enclosing your numerical value in quotes:

.. code-block:: yaml

  # This may return a "must be of type string" error
  my-stack-definition:
    template_path: ./my-templates/my-cloudformation-template.yaml
    tags:
      CostCenter: "1234"

******************
Updates to Lookups
******************

Some lookup usage may have changed slightly. Here's some examples:

.. code-block:: yaml

  # This generates a deprecation warning in newer Runway versions
  VpcId: ${rxref vpc::VpcId}

  # This is the new usage
  VpcId: ${rxref vpc.VpcId}

.. code-block:: yaml

  # This generates an unknown lookup error
  SlackUrl: ${ssmstore us-east-1@/devops/slack_hook}

  # This is the new usage
  SlackUrl: ${ssm /devops/slack_hook}

*********************************************************
Migration from upload_lambda_functions to PythonFunction Hook
*********************************************************

The ``runway.cfngin.hooks.aws_lambda.upload_lambda_functions`` hook is deprecated and slated for removal in Runway v3.0.0. The recommended replacement is the ``runway.cfngin.hooks.awslambda.PythonFunction`` hook (and related hooks like ``PythonLayer``).

The primary difference is that ``upload_lambda_functions`` managed multiple Lambda function packages within a single hook definition, whereas ``PythonFunction`` typically manages a single package per hook definition. This requires splitting one old hook definition into multiple new ones.

--------------------------
Configuration Changes
--------------------------

To migrate, replace your existing ``upload_lambda_functions`` hook definition with one or more ``PythonFunction`` definitions.

Key argument mappings:

*   **path:** Change from ``runway.cfngin.hooks.aws_lambda.upload_lambda_functions`` to ``runway.cfngin.hooks.awslambda.PythonFunction``.
*   **args.bucket** -> ``args.bucket_name``
*   **args.prefix** -> ``args.object_prefix``
*   **args.functions.<func_name>.path** -> ``args.source_code`` (in the corresponding new hook definition)
*   **args.functions.<func_name>.runtime** -> ``args.runtime``
*   **Dockerization:** ``PythonFunction`` uses Docker for building packages by default (especially when dependencies require it or when deploying cross-platform).
    *   If the old hook used ``dockerize_pip: true`` or ``dockerize_pip: non-linux``, you might not need explicit Docker configuration in the new hook unless you need to customize the Docker build (e.g., ``args.docker.file``, ``args.docker.image``).
    *   To *disable* Docker builds (equivalent to the old ``dockerize_pip: false``), use ``args.docker.disabled: true``.
*   **Include/Exclude:** ``PythonFunction`` uses ``.gitignore`` patterns within the ``source_code`` directory for determining package contents. You can add more patterns using ``args.extend_gitignore``. This replaces the old ``include`` and ``exclude`` arguments.
*   **data_key:** Each new ``PythonFunction`` hook definition *must* have a unique ``data_key`` assigned. This key is used to reference the hook's output data (e.g., S3 bucket/key) in your blueprints or templates.

--------------------------
Example Migration
--------------------------

**Before (using upload_lambda_functions):**

.. code-block:: yaml

  pre_build:
    - path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
      required: true
      data_key: lambda_upload  # Generic key for all functions in this hook
      args:
        bucket: ${var lambda_bucket_name}
        prefix: lambda-functions
        functions:
          api_handler:
            path: ./src/api_handler
            runtime: python3.9
            include:
              - "*.py"
            exclude:
              - "tests/"
              - "*.pyc"
          data_processor:
            path: ./src/data_processor
            runtime: python3.9
            dockerize_pip: true # Build using Docker

**After (using PythonFunction):**

.. code-block:: yaml

  pre_build:
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      required: true
      data_key: api_pkg  # Unique key for the API handler
      args:
        bucket_name: ${var lambda_bucket_name}
        object_prefix: lambda-functions
        source_code: ./src/api_handler
        runtime: python3.9
        # .gitignore in ./src/api_handler handles includes/excludes
        # Docker build disabled as it wasn't used before
        docker:
          disabled: true
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      required: true
      data_key: data_pkg # Unique key for the data processor
      args:
        bucket_name: ${var lambda_bucket_name}
        object_prefix: lambda-functions
        source_code: ./src/data_processor
        runtime: python3.9
        # Docker build enabled by default, no need for explicit arg
        # unless customization is needed.
        # .gitignore in ./src/data_processor handles includes/excludes

-----------------------------------
Updating Blueprint/Template Usage
-----------------------------------

Previously, you would access the build results using the hook's ``data_key`` and the function name:

.. code-block:: yaml

  # Example in a CFNgin blueprint/template variable definition
  MyApiFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        S3Bucket: ${hook_data lambda_upload.api_handler.Code.S3Bucket}
        S3Key: ${hook_data lambda_upload.api_handler.Code.S3Key}
      # ... other properties

The new, preferred method uses dedicated ``${awslambda...}`` lookups, referencing the specific ``data_key`` you assigned to the ``PythonFunction`` hook:

.. code-block:: yaml

  # Example using ${awslambda...} lookups
  MyApiFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        S3Bucket: ${awslambda.S3Bucket api_pkg}  # Use data_key 'api_pkg'
        S3Key: ${awslambda.S3Key api_pkg}        # Use data_key 'api_pkg'
      Runtime: ${awslambda.Runtime api_pkg}      # Get runtime if needed
      Handler: index.handler                     # Example handler
      CodeSha256: ${awslambda.CodeSha256 api_pkg} # For drift detection
      # ... other properties

  MyDataProcessorFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        S3Bucket: ${awslambda.S3Bucket data_pkg} # Use data_key 'data_pkg'
        S3Key: ${awslambda.S3Key data_pkg}       # Use data_key 'data_pkg'
      Runtime: ${awslambda.Runtime data_pkg}
      Handler: process.handler                   # Example handler
      CodeSha256: ${awslambda.CodeSha256 data_pkg}
      # ... other properties

You can also access attributes directly from the hook data object (e.g., ``${hook_data api_pkg.S3Bucket}``), but the dedicated lookups are generally recommended for clarity and future compatibility.
