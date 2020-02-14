.. _kubectl: https://kubernetes.io/docs/reference/kubectl/overview/
.. _Serverless Framework: https://serverless.com/
.. _Terraform: https://www.terraform.io

.. _commands:

########
Commands
########


.. _command-deploy:

******
deploy
******

.. file://./../../runway/_cli/commands/_deploy.py

Used to deploy :ref:`modules<runway-module>` with Runway.

When this command is used, the following will take place:

1. The :ref:`deploy environment <term-deploy-env>` will be determined from one of the following (in order of precedence):

  - ``-e, --deploy-environment`` option
  - **DEPLOY_ENVIRONMENT** environment variable
  - git branch (unless **ignore_git_branch** is enabled in the :ref:`runway-config`)
  - directory

2. The :ref:`deployment(s)<runway-deployment>` and :ref:`module(s)<runway-module>` to deploy will be selected.
   This will occur in one of three ways:

  - *(default)* Runway will prompt the user to make selections manually
  - if ``--tag`` is provided, all modules containing **all** tags will be selected
  - if Runway is run non-interactively, all deployments and modules will be selected

3. Runway will iterate through all of the selected deployments and modules, deploying them in the order defined.


.. rubric:: Usage
.. code-block:: text

  $ runway deploy [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway deploy
  $ runway deploy --ci --deploy-environment example
  $ runway deploy --tag tag1 --tag tag2

----


.. _command-destroy:

*******
destroy
*******

.. file://./../../runway/_cli/commands/_destroy.py

Used to destroy :ref:`modules<runway-module>` with Runway.

.. danger:: Use extreme caution when run non-interactively or using ``--tag <tag>...``.
            You will **not** be prompted before deletion.
            All modules (or those selected by tag) will be **irrecoverably deleted**.

When this command is used, the following will take place:

1. The :ref:`deploy environment <term-deploy-env>` will be determined from one of the following (in order of precedence):

  - ``-e, --deploy-environment`` option
  - **DEPLOY_ENVIRONMENT** environment variable
  - git branch (unless **ignore_git_branch** is enabled in the :ref:`runway-config`)
  - directory

2. The :ref:`deployment(s)<runway-deployment>` and :ref:`module(s)<runway-module>` to deploy will be selected.
   This will occur in one of three ways:

  - *(default)* Runway will prompt the user to make selections manually
  - if ``--tag`` is provided, all modules containing **all** tags will be selected
  - if Runway is run non-interactively, all deployments and modules will be selected

3. Runway will iterate through all of the selected deployments and modules, destroying them in reverse of the order defined.


.. rubric:: Usage
.. code-block:: text

  $ runway destroy [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway destroy
  $ runway destroy --ci --deploy-environment example
  $ runway destroy --tag tag1 --tag tag2

----


.. _command-dismantle:

*********
dismantle
*********

.. file://./../../runway/_cli/commands/_dismantle.py

Alias of :ref:`command-destroy`.


.. rubric:: Usage
.. code-block:: text

  $ runway dismantle [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway dismantle
  $ runway dismantle --ci --deploy-environment example
  $ runway dismantle --tag tag1 --tag tag2

----


.. _command-envvars:

*******
envvars
*******

.. file://./../../runway/_cli/commands/_envvars.py

Output **env_vars** defined in the :ref:`runway-config`.

OS environment variables can be set in the :ref:`runway-config` for different :ref:`deploy environments<term-deploy-env>` (e.g. dev & prod ``KUBECONFIG`` values).
This command allows access to these values for use outside of Runway.

.. note:: Only outputs **env_vars** defined in deployments, not modules.

.. rubric:: Usage
.. code-block:: text

  $ runway envvars [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway envvars
  $ eval "$(runway envvars)"
  $ runway envvars --deploy-environment example

----


.. _command-docs:

****
docs
****

.. file://./../../runway/_cli/commands/_docs.py

Open the Runway documentation web site using the default web browser.


.. rubric:: Usage
.. code-block:: text

  $ runway docs [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway docs

----


.. _command-gen-sample:

**********
gen-sample
**********

.. file://./../../runway/_cli/commands/_gen_sample/__init__.py

Generate a sample :ref:`Runway module<runway-module>` directory or project.

The sample is created in the current directory.
If a directory already exists with the name Runway tries to use, the sample will not be created.

.. rubric:: Available Samples

+--------------------+---------------------------------------------------+
|       Name         |  Description                                      |
+====================+===================================================+
| ``cdk-csharp``     | :ref:`mod-cdk` using C#                           |
+--------------------+---------------------------------------------------+
| ``cdk-py``         | :ref:`mod-cdk` using Python                       |
+--------------------+---------------------------------------------------+
| ``cdk-tsc``        | :ref:`mod-cdk` using TypeScript                   |
+--------------------+---------------------------------------------------+
| ``cfn``            | :ref:`CloudFormation <mod-cfn>` stack with S3     |
|                    | bucket & DDB table (perfect for storing Terraform_|
|                    | backend state)                                    |
+--------------------+---------------------------------------------------+
| ``cfngin``         | :ref:`Troposphere <mod-cfn>` identical to the     |
|                    | ``cfn`` sample but written in Python              |
+--------------------+---------------------------------------------------+
| ``k8s-cfn-repo``   | :ref:`mod-k8s` EKS cluster & sample app using     |
|                    | CloudFormation                                    |
+--------------------+---------------------------------------------------+
| ``k8s-tf-repo``    | :ref:`mod-k8s` EKS cluster & sample app using     |
|                    | Terraform_                                        |
+--------------------+---------------------------------------------------+
| ``k8s-flux-repo``  | `Kubernetes + Flux`_                              |
|                    | :ref:`module<runway-module>` EKS cluster & Flux   |
|                    | app using Terraform                               |
+--------------------+---------------------------------------------------+
| ``sls-py``         | `Serverless Framework`_                           |
|                    | :ref:`module<runway-module>` using Python         |
+--------------------+---------------------------------------------------+
| ``sls-tsc``        | :ref:`mod-sls` using TypeScript                   |
+--------------------+---------------------------------------------------+
| ``static-angular`` | :ref:`mod-staticsite` using Angular               |
+--------------------+---------------------------------------------------+
| ``static-react``   | :ref:`mod-staticsite` using React                 |
+--------------------+---------------------------------------------------+
| ``tf``             | :ref:`mod-tf`                                     |
+--------------------+---------------------------------------------------+


.. rubric:: Usage
.. code-block:: text

  $ runway gen-sample [OPTIONS] <sample>


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway gen-sample cfngin
  $ runway gen-sample static-react

----


.. _command-init:

****
init
****

.. file://./../../runway/_cli/commands/_envvars.py

Creates a sample :ref:`runway-config` in the current directory.

.. rubric:: Usage
.. code-block:: text

  $ runway init [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway init
  $ runway init --debug

----


.. _command-kbenv:
.. _command-kbenv-install:

*************
kbenv install
*************

.. file://./../../runway/_cli/commands/_kbenv/_install.py

Install the specified version of kubectl_ (e.g. v1.14.0).

If no version is specified, Runway will attempt to find and read a ``.kubectl-version`` file in the current directory (see :ref:`k8s-version` for more details).
If this file doesn't exist, nothing will be installed.

Compatible with `alexppg/kbenv <https://github.com/alexppg/kbenv>`__.

.. rubric:: Usage
.. code-block:: text

  $ runway kbenv install [OPTIONS] [<version>]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway kbenv install
  $ runway kbenv install v1.14.0

----


.. _command-kbenv-run:

*********
kbenv run
*********

.. file://./../../runway/_cli/commands/_kbenv/_install.py

Run a kubectl_ command.

Uses the version of kubectl_ specified in the ``.kubectl-version`` file in the current directory (see :ref:`k8s-version` for more details).

.. important:: When using options shared with Runway, ``--`` **must** be placed before the kubectl_ command.

.. rubric:: Usage
.. code-block:: text

  $ runway kbenv run [OPTIONS] [<version>]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway kbenv run version --client
  $ runway kbenv run -- --help

----


.. _command-plan:

****
plan
****

.. file://./../../runway/_cli/commands/_plan.py

Determine what infrastructure changes will occur during the next :ref:`command-deploy`.

.. note:: Currently only supported for :ref:`mod-cdk`, :ref:`mod-cfn`, and :ref:`mod-tf`.

When this command is used, the following will take place:

1. The :ref:`deploy environment <term-deploy-env>` will be determined from one of the following (in order of precedence):

  - ``-e, --deploy-environment`` option
  - **DEPLOY_ENVIRONMENT** environment variable
  - git branch (unless **ignore_git_branch** is enabled in the :ref:`runway-config`)
  - directory

2. The :ref:`deployment(s)<runway-deployment>` and :ref:`module(s)<runway-module>` to deploy will be selected.
   This will occur in one of three ways:

  - *(default)* Runway will prompt the user to make selections manually
  - if ``--tag`` is provided, all modules containing **all** tags will be selected
  - if Runway is run non-interactively, all deployments and modules will be selected

3. Runway will iterate through all of the selected deployments and modules, attempting to determine the changes will occur during the next :ref:`command-deploy`.


.. rubric:: Usage
.. code-block:: text

  $ runway plan [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway plan
  $ runway plan --ci --deploy-environment example
  $ runway plan --tag tag1 --tag tag2

----


.. _command-preflight:

*********
preflight
*********

.. file://./../../runway/_cli/commands/_preflight.py

Alias of :ref:`command-test`.


.. rubric:: Usage
.. code-block:: text

  $ runway preflight [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway preflight

----


.. _command-run-aws:

*******
run-aws
*******

.. file://./../../runway/_cli/commands/_run_aws.py

Execute awscli commands using the version bundled with Runway.

This command gives access to the awscli when it might not otherwise be installed (e.g. when using a binary release of Runway).

.. important:: When using options shared with Runway, ``--`` **must** be placed before the awscli command.


.. rubric:: Usage
.. code-block:: text

  $ runway run-aws [OPTIONS] <args>


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway run-aws sts get-caller-identity
  $ runway run-aws -- --version

----


.. _command-run-python:

**********
run-python
**********

.. file://./../../runway/_cli/commands/_run_python.py

Execute a python script using a bundled copy of python.

This command can execute actions using python without requiring python to be installed on a system.
This is only applicable when installing a binary release of Runway (not installed from PyPi).
When installed from PyPI, the current interpreter is used.


.. rubric:: Usage
.. code-block:: text

  $ runway run-python [OPTIONS] <filename>


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway run-python my_script.py

----


.. _command-run-stacker:

***********
run-stacker
***********

.. file://./../../runway/_cli/commands/_run_stacker.py

Execute the "shimmed" `Stacker <https://stacker.readthedocs.io/en/stable/>`__ aka :ref:`Runway CFNgin <mod-cfn>`.

This command allows direct access to Runway's CloudFormation management tool.

.. deprecated:: 1.5.0

.. important:: When using options shared with Runway, ``--`` **must** be placed before the Stacker command.


.. rubric:: Usage
.. code-block:: text

  $ runway run-stacker [OPTIONS] <args>


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway run-stacker build cfngin_config.yml
  $ runway run-stacker -- info --help

----


.. _command-takeoff:

*******
takeoff
*******

.. file://./../../runway/_cli/commands/_takeoff.py

Alias of :ref:`command-deploy`


.. rubric:: Usage
.. code-block:: text

  $ runway takeoff [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway takeoff
  $ runway takeoff --ci --deploy-environment example
  $ runway takeoff --tag tag1 --tag tag2

----


.. _command-taxi:

****
taxi
****

.. file://./../../runway/_cli/commands/_taxi.py

Alias of :ref:`command-plan`.


.. rubric:: Usage
.. code-block:: text

  $ runway taxi [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --ci                            Run in non-interactive mode.
  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --tag <tag>...                  Select modules by tag or tags.
                                  This option can be specified more than once to
                                  build a list of tags that are treated as "AND".
                                  (e.g. "--tag <tag1> --tag <tag2>" would select
                                  all modules with BOTH tags).
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway taxi
  $ runway taxi --ci --deploy-environment example
  $ runway taxi --tag tag1 --tag tag2

----


.. _command-test:

****
test
****

.. file://./../../runway/_cli/commands/_test.py

Execute :ref:`tests<runway-test>` as defined in the :ref:`runway-config`.

If one of the tests fail, the command will exit immediately unless the ``required`` option is set to ``false`` for the failing test.
If it is not required, the next test will be executed.
If any tests fail, the command with exit with a non-zero exit code.


.. rubric:: Usage
.. code-block:: text

  $ runway test [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  -e, --deploy-environment <env-name>
                                  Manually specify the name of the deploy environment.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway test

----


.. _command-tfenv:
.. _command-tfenv-install:

*************
tfenv install
*************

.. file://./../../runway/_cli/commands/_tfenv/_install.py

Install the specified version of Terraform_ (e.g. 0.12.0).

If no version is specified, Runway will attempt to find and read a ``.terraform-version`` file in the current directory (see :ref:`tf-version` for more details).
If this file doesn't exist, nothing will be installed.


.. rubric:: Usage
.. code-block:: text

  $ runway tfenv install [OPTIONS] [<version>]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway tfenv install 0.12.0

----


.. _command-tfenv-run:

*********
tfenv run
*********

.. file://./../../runway/_cli/commands/_tfenv/_run.py

Run a Terraform_ command.

Uses the version of Terraform_ specified in the ``.terraform-version`` file in the current directory (see :ref:`tf-version` for more details).

.. important:: When using options shared with Runway, ``--`` **must** be placed before the Terraform_ command.


.. rubric:: Usage
.. code-block:: text

  $ runway tfenv run [OPTIONS] <args>


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway tfenv run --version
  $ runway tfenv run -- --help

----


.. _command-whichenv:

********
whichenv
********

.. file://./../../runway/_cli/commands/_whichenv.py

Print the current :ref:`deploy environment <term-deploy-env>` name to stdout.

When run, the :ref:`deploy environment <term-deploy-env>`  will be determined from one of the following (in order of precedence):

- **DEPLOY_ENVIRONMENT** environment variable
- git branch (unless **ignore_git_branch** is enabled in the :ref:`runway-config`)
- directory


.. rubric:: Usage
.. code-block:: text

  $ runway whichenv [OPTIONS]


.. rubric:: Options
.. code-block:: text

  --debug                         Supply once to display Runway debug logs.
                                  Supply twice to display all debug logs.
  --no-color                      Disable color in Runway's logs.
  --verbose                       Display Runway verbose logs.


.. rubric:: Example
.. code-block:: shell

  $ runway whichenv
