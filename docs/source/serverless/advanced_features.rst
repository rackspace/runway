#################
Advanced Features
#################

Advanced features and detailed information for using Serverless Framework with Runway.


****************
Disabling NPM CI
****************

At the start of each module execution, Runway will execute ``npm ci`` to ensure
Serverless Framework is installed in the project (so Runway can execute it via
``npx sls``. This can be disabled (e.g. for use when the ``node_modules``
directory is pre-compiled) via the ``skip_npm_ci`` module option.

.. rubric:: Example
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: myslsproject.sls
          options:
            skip_npm_ci: true


*************************************
Promoting Builds Through Environments
*************************************

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

.. rubric:: Example
.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: myslsproject.sls
          options:
          promotezip:
            bucketname: my-build-account-bucket-name


*******************************************
Specifying Serverless CLI Arguments/Options
*******************************************

Runway can pass custom arguments/options to the Serverless CLI by using the ``args`` option.
These will always be placed after the default arguments/options.

The value of ``args`` must be a list of arguments/options to pass to the CLI.
Each element of the argument/option should be it's own list item (e.b. ``--config sls.yml`` would be ``['--config', 'sls.yml']``.

.. important::
  Do not provide ``--region <region>`` or ``--stage <stage>`` here.
  These will be provided by Runway.


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
