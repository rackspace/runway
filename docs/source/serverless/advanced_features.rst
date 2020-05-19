#################
Advanced Features
#################

Advanced features and detailed information for using Serverless Framework with Runway.


.. _sls-skip-npm-ci:

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


.. _sls-extend-yml:

*****************************************
Extending a Serverless Configuration File
*****************************************

Runway has the ability to extend the contents of a *serverless.yml* file using the value of the ``extend_serverless_yml`` option.
The value of this option is recursively merged into a resolved clone of the module's Serverless configuration.
To create this resolved clone, Runway uses "`serverless print`_" (including `args <sls-args>`_) to resolve the module's Serverless configuration file and output the contents to a temporary file.
The temporary file is deleted after each execution of Runway.

This functionality can be especially useful when used alongside :ref:`remote module paths <runway-module-path>` such as a module from a :ref:`git repository <runway-module-path-git>` to change values on the fly without needing to modify the source for small differences in each environment.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        - path: git::git://github.com/onicagroup/example.git//sampleapp?tag=v1.0.0
          options:
            extend_serverless_yml:
              custom:
                env:
                  memorySize: 512
      regions:
        - us-east-1


.. _serverless print: https://www.serverless.com/framework/docs/providers/aws/cli-reference/print/

Merge Logic
===========

The two data sources are merged by iterating over their content and combining the lowest level nodes possible.

.. rubric:: Example

**serverless.yml**

.. code-block:: yaml

  functions:
    example:
      handler: handler.example
      runtime: python3.8
      memorySize: 512

**runway.yml**

.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp.sls
          options:
            extend_serverless_yml:
              functions:
                example:
                  memorySize: 1024
              resources:
                Resources:
                  ExampleResource:
                    Type: AWS::CloudFormation::WaitConditionHandle
      regions:
        - us-east-1

Result

.. code-block:: yaml

  functions:
    example:
      handler: handler.example
      runtime: python3.8
      memorySize: 1024
    resources:
      Resources:
        ExampleResource:
          Type: AWS::CloudFormation::WaitConditionHandle


.. _sls-promotezip:

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


.. _sls-args:

*******************************************
Specifying Serverless CLI Arguments/Options
*******************************************

Runway can pass custom arguments/options to the Serverless CLI by using the ``args`` option.
These will always be placed after the default arguments/options.

The value of ``args`` must be a list of arguments/options to pass to the CLI.
Each element of the argument/option should be it's own list item (e.g. ``--config sls.yml`` would be ``['--config', 'sls.yml']``).

.. important::
  Do not provide ``--region <region>`` or ``--stage <stage>`` here, these will be provided by Runway.
  Runway will also provide ``--no-color`` if stdout is not a TTY.


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
      regions:
        - us-east-2
      environments:
        example: true

.. rubric:: Command Equivalent
.. code-block::

  serverless deploy -r us-east-1 --stage example --config sls.yml
