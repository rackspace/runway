.. _sls-configuration:

#############
Configuration
#############

Standard `Serverless Framework <https://serverless.com>`__ rules apply but, we have some added prerequisites, recommendations, and caveats.



*************
Prerequisites
*************

- `npm installed on the system <https://www.npmjs.com/get-npm>`__
- Serverless must be a dev dependency of the module (e.g. ``npm install --save-dev serverless``)

We strongly recommend you commit the package-lock.json that is generated after running ``npm install``.


*******
Options
*******

Options specific to Serverless Framework modules.

.. data:: args
  :type: Optional[List[str]]
  :value: []
  :noindex:

  List of CLI arguments/options to pass to the Serverless Framework CLI.
  See :ref:`Specifying Serverless CLI Arguments/Options <sls-args>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      args:
        - '--config'
        - sls.yml

  .. versionadded:: 1.4.0

.. data:: extend_serverless_yml
  :type: Optional[Dict[str, Any]]
  :value: {}
  :noindex:

  If provided, the value of this option will be recursively merged into the modules *serverless.yml* file.
  See :ref:`Extending a Serverless Configuration File <sls-extend-yml>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      extend_serverless_yml:
        custom:
          env:
            memorySize: 512

  .. versionadded:: 1.8.0

.. data:: promotezip
  :type: Optional[Dict[str, str]]
  :value: {}
  :noindex:

  If provided, promote Serverless Framework generated zip files between environments from a *build* AWS account.
  See :ref:`Promoting Builds Through Environments <sls-promotezip>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      promotezip:
        bucketname: my-build-account-bucket-name

.. data:: skip_npm_ci
  :type: bool
  :value: False
  :noindex:

  Skip running ``npm ci`` in the module directory prior to processing the module.
  See :ref:`Disabling NPM CI <sls-skip-npm-ci>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      skip_npm_ci: true


**************
serverless.yml
**************

Refer to the `Serverless Framework Documentation <https://serverless.com/framework/docs/>`_.


******
Stages
******

Runway's concept of a :term:`Deploy Environment` has a 1-to-1 mapping to Serverless's **stage**.
For example, if the deploy environment is **dev**, Serverless will be run with ``--stage dev``.

Each stage requires either its own variables file (even if empty for a particular stage) following a specific `File Naming`_ scheme and/or a configured ``environment`` for the module or deployment (see :ref:`Runway Config File <runway-config>` for details).

File Naming
===========

- ``env/STAGE-REGION.yml``
- ``config-STAGE-REGION.yml``
- ``env/STAGE.yml``
- ``config-STAGE.yml``
- ``env/STAGE-REGION.json``
- ``config-STAGE-REGION.json``
- ``env/STAGE.json``
- ``config-STAGE.json``
