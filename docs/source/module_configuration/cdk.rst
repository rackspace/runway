.. _Lookups: ../lookups.html

.. _mod-cdk:

CDK
===

Standard `AWS CDK
<https://awslabs.github.io/aws-cdk/>`_ rules apply, with the following recommendations/caveats:

A ``package.json`` file is required, specifying the aws-cdk dependency. E.g.::

    {
      "name": "mymodulename",
      "version": "1.0.0",
      "description": "My CDK module",
      "main": "index.js",
      "dependencies": {
        "@aws-cdk/cdk": "^0.9.2",
        "@types/node": "^10.10.1"
      },
      "devDependencies": {
        "aws-cdk": "^0.9.2",
        "typescript": "^3.0.3"
      }
      "author": "My Org",
      "license": "Apache-2.0"
    }

We strongly recommend you commit the package-lock.json that is generated after running ``npm install``


Build Steps
-----------

Build steps (e.g. for compiling TypeScript) can be specified in the module options. These steps will be run before each diff, deploy, or destroy.
::

    deployments:
      - modules:
          - path: mycdkmodule
            environments:
              dev: true
            options:
              build_steps:
                - npx tsc


Environment Configs
-------------------

Environments can be specified via deployment and/or module options. Each example below shows the explicit CDK ``ACCOUNT/REGION`` environment mapping;
these can be alternately be specified with a simple boolean (e.g. ``dev: true``).


Top-level Runway Config
~~~~~~~~~~~~~~~~~~~~~~~

::

    ---

    deployments:
      - modules:
          - path: mycdkmodule
            environments:
              # CDK environment values can be specified in 3 forms:
              # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
              # dev:
              #   route_53_zone_id: Z3P5QSUBK4POTI
              # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
              # dev: 987654321098/us-west-2
              # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
              # dev: true

and/or:
::

    ---

    deployments:
      - environments:
          # CDK environment values can be specified in 3 forms:
          # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
          # dev:
          #   route_53_zone_id: Z3P5QSUBK4POTI
          # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
          # dev: 987654321098/us-west-2
          # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
          # dev: true
        modules:
          - mycdkmodule


In Module Directory
~~~~~~~~~~~~~~~~~~~

.. important:: `Lookups`_ are not supported in this file.

::

    ---
    environments:
      # CDK environment values can be specified in 3 forms:
      # Opt 1 - A yaml mapping, in which case each key:val pair will be provided as context options
      # dev:
      #   route_53_zone_id: Z3P5QSUBK4POTI
      # Opt 2 - A string, in which case the explicit CDK ``ACCOUNT/REGION`` environment will be verified
      # dev: 987654321098/us-west-2
      # Opt 3 - Booleans, in which case the module will always be deployed in the given environment
      # dev: true

(in ``runway.module.yml``)

Disabling NPM CI
----------------
At the start of each module execution, Runway will execute ``npm ci`` to ensure
the CDK is installed in the project (so Runway can execute it via
``npx cdk``. This can be disabled (e.g. for use when the ``node_modules``
directory is pre-compiled) via the ``skip_npm_ci`` module option:
::

    ---
    deployments:
      - modules:
          - path: mycdkproject.cdk
            options:
              skip_npm_ci: true
