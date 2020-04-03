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


************
Environments
************

Unlike some other module types, CDK does not have file that can be used to configure an environment.
It can only be configured using the ``environments`` option of a deployment and/or module (see :ref:`Runway Config File <runway-config>` for details).


Runway Config
=============

.. rubric:: Top-level
.. code-block:: yaml

  ---
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

.. rubric:: In Module Directory
.. code-block:: yaml

  ---
  environments:
    dev: true
    prod: true
