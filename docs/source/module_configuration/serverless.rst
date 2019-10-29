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

::

    ---
    environments:
      dev: true
      prod: true

(in ``runway.module.yml``)

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
