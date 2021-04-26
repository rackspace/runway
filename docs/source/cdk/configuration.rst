#############
Configuration
#############

Standard `CDK <https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html>`__ rules apply but, we have some added prerequisites, recommendations, and caveats.

.. contents::
  :depth: 4


*************
Prerequisites
*************

- `npm installed on the system <https://www.npmjs.com/get-npm>`__
- CDK must be a dev dependency of the module (e.g. ``npm install --save-dev aws-cdk``)

We strongly recommend you commit the package-lock.json that is generated after running ``npm install``.


************
Environments
************

Unlike some other module types, CDK does not have a file that can be used to configure an environment.
It can only be configured using the :attr:`deployment.environments`/:attr:`module.environments` field.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: mycdkmodule.cdl
          environments:
            dev: true
            prod: true
    - modules:
        - path: myothercdkmodule.cdk
      environments:
        dev: true
        prod: true


.. _cdk.options:

*******
Options
*******

.. _cdk.build_steps:

.. data:: build_steps
  :type: Optional[List[str]]
  :value: None
  :noindex:

  Shell commands to be run before processing the module.

  See :ref:`Build Steps <cdk.Build Steps>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      build_steps:
        - npx tsc


.. _cdk.skip_npm_ci:

.. data:: skip_npm_ci
  :type: bool
  :value: False
  :noindex:

  See :ref:`Disable NPM CI <cdk.Disabling NPM CI>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      skip_npm_ci: true
