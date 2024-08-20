.. _cdk-configuration:

#############
Configuration
#############

Standard `CDK <https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html>`__ rules apply but, we have some added prerequisites, recommendations, and caveats.



*************
Prerequisites
*************

- `npm installed on the system <https://www.npmjs.com/get-npm>`__
- CDK must be a dev dependency of the module (e.g. ``npm install --save-dev aws-cdk``)

We strongly recommend you commit the package-lock.json that is generated after running ``npm install``.


***************
Recommendations
***************


Feature Flags
=============

The AWS CDK uses `feature flags <https://docs.aws.amazon.com/cdk/latest/guide/featureflags.html>`__ to enable potentially breaking behaviors prior to the next major release that makes them default behaviors.
Flags are stored as Runtime context values in ``cdk.json`` (or ``~/.cdk.json``).

.. sphinx doesn't like displaying these feature flags as `data` so they have to be headers

aws-cdk:enableDiffNoFail
------------------------

This feature flag is available in version ``^1.0.0``.

If this is set to ``true`` (recommend), ``cdk diff`` will always exit with ``0``.
With this set to ``false``, ``cdk diff`` will exit with a non-zero exit code if there is a diff.
This will result in Runway exiting before all stacks/modules/deployments are processed.

.. rubric:: Example
.. code-block:: json

  {
    "context": {
      "aws-cdk:enableDiffNoFail": true
    },
  }


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
  :type: list[str] | None
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

  Skip running ``npm ci`` in the module directory prior to processing the module.
  See :ref:`Disable NPM CI <cdk.Disabling NPM CI>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      skip_npm_ci: true
