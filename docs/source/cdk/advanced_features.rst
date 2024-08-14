.. _cdk-advanced-features:

#################
Advanced Features
#################

Advanced features and detailed information for using CDK with Runway.



.. _cdk.Build Steps:

***********
Build Steps
***********

Build steps (e.g. for compiling TypeScript) can be specified in :attr:`deployment.module_options`/:attr:`module.options`.
These steps will be run before each diff, deploy, or destroy.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: mycdkmodule.cdk
          environments:
            dev: true
          options:
            build_steps:
              - npx tsc


.. _cdk.Disabling NPM CI:

****************
Disabling NPM CI
****************

At the start of each module execution, Runway will execute ``npm ci`` to ensure that CDK is installed in the project (so Runway can execute it via ``npx cdk``).
This can be disabled (e.g. for use when the ``node_modules`` directory is pre-compiled) via the ``skip_npm_ci`` field of :attr:`deployment.module_options`/:attr:`module.options`.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: mycdkmodule.cdk
          options:
            skip_npm_ci: true
