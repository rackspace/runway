Basic Concepts
==============

Region
^^^^^^
- any AWS region

Module
^^^^^^
- A set of related AWS resources deployed using the same tool
- the tools supported by Runway out of the box are the following:

  * Cloudformation (using `Stacker <https://stacker.readthedocs.io/en/latest>`_)
  * `Terraform <https://www.terraform.io/docs/index.html>`_
  * `Serverless <https://serverless.com/framework/docs/>`_
  * `Cloud Development Kit <https://github.com/awslabs/aws-cdk>`_ (CDK)
  * static web sites **((need more details on this somewhere))**

Deployment
^^^^^^^^^^
- A set of related modules of any type, along with a list of regions they can be deployed to

  * for example, a Terraform module to create a database and a Serverless module for the application using the database

Project
^^^^^^^
- One or more deployments, specified in a ``runway.yml`` file

Environment
^^^^^^^^^^^
- The name of a particular instance of a project, where each instance of a project exists independent of all
  others, even if deployed in the same region and account
- Corresponds to a Serverless stage, a Terraform workspace, etc.
- typical names would be "dev", "qa" and "prod"

  * can also be for specific people ("dev-alice", "dev-bob"), tickets ("qa-234") or for any other reason

- Each environment will have its own unique set of configuration values


THIS NEEDS TO GO ELSEWHERE
^^^^^^^^^^^^^^^^^^^^^^^^^^
under "HOw to Use"?  It's too much detail, here

- May include IAM roles needed to perform the deployment

- When the ``CI`` environment variable is set, all deployments are run in order; otherwise,
  the user is prompted for deployments to run.


 - Environments are specified by one of three methods:
    a. The ``DEPLOY_ENVIRONMENT`` environment variable
    b. The name of the checked out Git branch
    c. The name of the folder containing the ``runway.yml`` file


     We recommend promoting changes through clear environment branches
       (prefixed with ``ENV-``). For example, when running a deployment in the ``ENV-dev`` branch
       dev will be the environment. The master branch can also be used as a special 'shared'
       environment called common (e.g. for modules not normally promoted through other
       environments).
    b. The parent folder name of each module. For teams with a preference or technical
       requirement to not use git branches, each environment can be represented on disk
       as a folder. Instead of promoting changes via git merges, changes can be promoted
       by copying the files between the environment folders. See the ``ignore_git_branch``
       runway.yml config option.

        - The folder name of the module itself (not its parent folder) if the
          ignore_git_branch and current_dir runway.yml config config options are both
          used (see "Directories as Environments with a Single Module" in "Repo Structure").
