Basic Concepts
==============

Modules
^^^^^^^
- A single-tool configuration of an application/component/infrastructure (e.g. a set of 
  CloudFormation stacks to deploy a VPC, a Serverless or CDK app)

Regions
^^^^^^^
- AWS regions

Environments
^^^^^^^^^^^^
 - A Serverless stage, a Terraform workspace, etc.
 - Environments are determined automatically from
    a. Git branches. We recommend promoting changes through clear environment branches 
       (prefixed with ENV-). For example, when running a deployment in the ENV-dev branch 
       dev will be the environment. The master branch can also be used as a special 'shared' 
       environment called common (e.g. for modules not normally promoted through other 
       environments).
    b. The parent folder name of each module. For teams with a preference or technical 
       requirement to not use git branches, each environment can be represented on disk 
       as a folder. Instead of promoting changes via git merges, changes can be promoted 
       by copying the files between the environment folders. See the ignore_git_branch 
       runway.yml config option.

        - The folder name of the module itself (not its parent folder) if the 
          ignore_git_branch and current_dir runway.yml config config options are both 
          used (see "Directories as Environments with a Single Module" in "Repo Structure").
    c. The DEPLOY_ENVIRONMENT environment variable.

Deployments
^^^^^^^^^^^
- Mappings of modules to regions, optionally with AWS IAM roles to assume

runway.yml
^^^^^^^^^^
- List of deployments
- When the CI environment variable is set, all deployments are run in order; otherwise, 
  the user is prompted for deployments to run.