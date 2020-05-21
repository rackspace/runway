##############
Infrastructure
##############

The Runway repository uses some external infrastructure to run tests and server public content.
The code that deploys this infrastructure is located in the ``infrastructure/`` directory.
Each subdirectory is a logical separation between AWS accounts.


************************
Deploying Infrastructure
************************

Infrastructure can be deployed from the root of the ``infrastructure/`` directory for any environment.
We make use of ``make`` to simplify the process.

To execute Runway for an environment, use the following command syntax.

.. code-block:: shell

  $ make <runway-subcommand> <environment>

.. rubric:: Example
.. code-block:: shell

  $ make deploy public


******
public
******

AWS account for public facing assets.

.. rubric:: Onica SSO Name

onica-public-prod

.. rubric:: Resources

- public S3 bucket that houses build artifacts

  - binary executables

- IAM user used by GitHub Actions & it's policies

  - able to sync with the artifact bucket
  - add entries to a DynamoDB table for the ``oni.ca`` URL shortener app

    - path to download the binary executables from S3


*******
testing
*******

.. note:: Currently exists in the ``integration_test_infrastructure/`` directory as ``codebuild/``.

AWS account for running Runway integration and end-to-end tests.

.. rubric:: Onica SSO Name

onica-platform-runway-testing-lab

.. rubric:: Resources

TBA


***********
testing-alt
***********

.. note:: Currently exists in the ``integration_test_infrastructure/`` directory as ``alt_account_role/``.

AWS account for running Runway integration and end-to-end tests that require cross-account access to complete.

.. rubric:: Onica SSO Name

onica-platform-runway-testing-alt-lab

.. rubric:: Resources

TBA
