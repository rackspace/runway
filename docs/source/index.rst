####################
Runway Documentation
####################

Runway is a lightweight wrapper around infrastructure deployment (e.g. CloudFormation, Terraform, Serverless) & linting (e.g. yamllint) tools to ease management of per-environment configs & deployment.

Very simple configuration to:

- Perform automatic linting/verification
- Ensure deployments are only performed when an environment config is present
- Define an IAM role to assume for each deployment
- Wrangle Terraform backend/workspace configs w/ per-environment tfvars
- Avoid long-term tool lock-in

  - Runway is a simple wrapper around standard tools. It simply helps to
    avoid convoluted Makefiles / CI jobs

.. toctree::
   :maxdepth: 2
   :hidden:

   installation
   getting_started
   quickstart/index
   commands
   r4y_config
   module_configuration/index
   lookups
   defining_tests
   repo_structure
   terminology
   apidocs/index
   developers
   license

********************
Module Configuration
********************

CloudFormation & Troposphere
============================

The CloudFormation module type is deployed using Runway's CloudFormation engine (CFNgin).
It is able to deploy raw CloudFormation templates (JSON & YAML) and Troposphere_ templates that are written in the form of a :ref:`Blueprint`.

.. toctree::
   :caption: CloudFormation & Troposphere
   :maxdepth: 2
   :hidden:

   cfngin/configuration
   cfngin/directory_structure
   cfngin/advanced_features
   cfngin/migrating

.. _Troposphere: https://github.com/cloudtools/troposphere


******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
