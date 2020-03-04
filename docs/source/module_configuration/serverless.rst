.. _Lookups: ../lookups.html

.. _mod-sls:

Serverless
==========

Standard `Serverless
<https://serverless.com/framework/>`_ rules apply, with the following
recommendations/caveats:

- Runway environments map directly to Serverless stages.
- A ``package.json`` file is required, specifying the serverless dependency, e.g.:

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

- We strongly recommend you commit the package-lock.json that is generated
  after running ``npm install``
- Each stage requires either its own variables file (even if empty for a
  particular stage) in one of the following forms, or a configured environment
  in the module options (see ``Enabling Environments Via Runway
  Deployment/Module Options`` below):

- ``env/STAGE-REGION.yml``
- ``config-STAGE-REGION.yml``
- ``env/STAGE.yml``
- ``config-STAGE.yml``
- ``env/STAGE-REGION.json``
- ``config-STAGE-REGION.json``
- ``env/STAGE.json``
- ``config-STAGE.json``


Enabling Environments Via Runway Deployment/Module Options
----------------------------------------------------------

Environments can be specified via deployment and module options in lieu of
variable files.


Top-level Runway Config
~~~~~~~~~~~~~~~~~~~~~~~

::

    ---

    deployments:
      - modules:
          - path: myslsmodule
            environments:
              dev: true
              prod: true

and/or
::

    ---

    deployments:
      - environments:
          dev: true
          prod: true
        modules:
          - myslsmodule


In Module Directory
~~~~~~~~~~~~~~~~~~~

.. important:: `Lookups`_ are not supported in this file.

::

    ---
    environments:
      dev: true
      prod: true

(in ``runway.module.yml``)

Promoting Builds Through Environments
-------------------------------------

Serverless build ``.zips`` can be used between environments by setting the
``promotezip`` module option and providing a bucket name in which to cache
the builds.

The first time the Serverless module is deployed using this option, it will
build/deploy as normal and cache the artifact on S3. On subsequent deploys,
Runway will used that cached artifact (finding it by comparing the module
source code).

This enables a common build account to deploy new builds in a dev/test
environment, and then promote that same zip through other environments
(any of these environments can be in the same or different AWS accounts).

The CloudFormation stack deploying the zip will be re-generated on each
deployment (so environment-specific values/lookups will work as normal).

Example config:
::

    ---
    deployments:
      - modules:
        - path: myslsproject.sls
          options:
            promotezip:
              bucketname: my-build-account-bucket-name


Disabling NPM CI
----------------
At the start of each module execution, Runway will execute ``npm ci`` to ensure
Serverless Framework is installed in the project (so Runway can execute it via
``npx sls``. This can be disabled (e.g. for use when the ``node_modules``
directory is pre-compiled) via the ``skip_npm_ci`` module option:
::

    ---
    deployments:
      - modules:
          - path: myslsproject.sls
            options:
              skip_npm_ci: true

Specifying Serverless CLI Arguments/Options
-------------------------------------------

Runway can pass custom arguments/options to the Serverless CLI by using the ``args`` option. These will always be placed after the default arguments/options

The value of ``args`` must be a list of arguments/options to pass to the CLI.
Each element of the argument/option should be it's own list item (e.b. ``--config sls.yml`` would be ``['--config', 'sls.yml']``.

.. important:: Do not provide ``--region <region>`` or ``--stage <stage>`` here. These will be provided by Runway.


.. rubric:: Runway Example
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp.sls
          options:
            args:
              - '--config'
              - sls.yml
      regions
        - us-east-2
      environments:
        example: true

.. rubric:: Command Equivalent
.. code-block::

  serverless deploy -r us-east-1 --stage example --config sls.yml
