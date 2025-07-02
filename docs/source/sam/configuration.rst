############
Configuration
############

Standard `AWS SAM CLI <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>`__ rules apply but, we have some added functionality.

**Supported SAM CLI Versions:** ``>=1.0.0``

*************
Configuration
*************

Configuration options for AWS SAM modules can be specified as ``module_options`` or ``options``.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.sam
          options:
            build_args:
              - --use-container
            deploy_args:
              - --guided
            skip_build: false

.. automodule:: runway.config.models.runway.options.sam
  :members:
  :exclude-members: model_config, model_fields

*****************
Runway Config Dir
*****************

Runway will change to the directory containing the SAM template file before executing SAM CLI commands.

*******************
Environment Support
*******************

Runway will look for SAM configuration files in the following order:

1. ``samconfig-<stage>-<region>.toml``
2. ``samconfig-<stage>.toml``
3. ``samconfig.toml``

Where ``<stage>`` is the current Runway environment name and ``<region>`` is the current AWS region.

*****************
Template Location
*****************

Runway will automatically detect SAM template files in the following order:

1. ``template.yaml``
2. ``template.yml``
3. ``sam.yaml``
4. ``sam.yml``

*****************
Parameter Support
*****************

Runway supports passing parameters to SAM deployments through the ``parameters`` configuration option. These parameters will be passed to the SAM CLI as ``--parameter-overrides``.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.sam
          parameters:
            Stage: ${env DEPLOY_ENVIRONMENT}
            BucketName: my-bucket-${env DEPLOY_ENVIRONMENT}

*************
Build Support
*************

By default, Runway will run ``sam build`` before deploying. This can be disabled by setting ``skip_build: true`` in the module options.

Additional build arguments can be passed using the ``build_args`` option.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.sam
          options:
            build_args:
              - --use-container
              - --parallel
            skip_build: false

**************
Deploy Support
**************

Additional deploy arguments can be passed using the ``deploy_args`` option.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.sam
          options:
            deploy_args:
              - --guided
              - --capabilities
              - CAPABILITY_IAM
