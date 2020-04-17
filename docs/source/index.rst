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
   runway_config
   module_configuration/index
   lookups
   defining_tests
   repo_structure
   terminology
   apidocs/index
   developers/index
   license


********************
Module Configuration
********************


.. _mod-cdk:

AWS Cloud Development Kit (CDK)
===============================

The CDK module type is deployed using the `AWS Cloud Development Kit (CDK) <https://docs.aws.amazon.com/cdk/latest/guide/home.html>`__.
Runway uses `system installed npm <https://www.npmjs.com/get-npm>`__ to install the CDK per-module.
This means that the CDK must be included as a dev dependency in the **package.json** of the module.

- `Configuration <cdk/configuration.html>`__
- `Directory Structure <cdk/directory_structure.html>`__
- `Advanced Features <cdk/advanced_features.html>`__

.. toctree::
   :caption: AWS Cloud Development Kit (CDK)
   :maxdepth: 2
   :hidden:

   cdk/configuration
   cdk/directory_structure
   cdk/advanced_features


CloudFormation & Troposphere
============================

The CloudFormation module type is deployed using Runway's CloudFormation engine (CFNgin).
It is able to deploy raw CloudFormation templates (JSON & YAML) and Troposphere_ templates that are written in the form of a :ref:`Blueprint`.

- `Configuration <cfngin/configuration.html>`__
- `Directory Structure <serverless/directory_structure.html>`__
- `Advanced Features <cfngin/advanced_features.html>`__

.. toctree::
   :caption: CloudFormation & Troposphere
   :maxdepth: 2
   :hidden:

   cfngin/configuration
   cfngin/directory_structure
   cfngin/advanced_features
   cfngin/migrating

.. _Troposphere: https://github.com/cloudtools/troposphere


.. _mod-sls:

Serverless Framework
====================

The Serverless module type is deployed using the `Serverless Framework <https://serverless.com>`__.
Runway uses `system installed npm <https://www.npmjs.com/get-npm>`__ to install Serverless per-module.
This means that Serverless must be included as a dev dependency in the **package.json** of the module.

- `Configuration <serverless/configuration.html>`__
- `Directory Structure <serverless/directory_structure.html>`__
- `Advanced Features <serverless/advanced_features.html>`__

.. toctree::
   :caption: Serverless Framework
   :maxdepth: 2
   :hidden:

   serverless/configuration
   serverless/directory_structure
   serverless/advanced_features


.. _mod-tf:

Terraform
=========

Runway provides a simple way to run the Terraform versions you want with variable values specific to each environment.
Terraform does not need to be installed prior to using this module type.
Runway maintains a cache of Terraform versions on a system, downloading and installing different versions as needed.

- `Configuration <terraform/configuration.html>`__
- `Directory Structure <terraform/directory_structure.html>`__
- `Advanced Features <terraform/advanced_features.html>`__

.. toctree::
   :caption: Terraform
   :maxdepth: 2
   :hidden:

   terraform/configuration
   terraform/directory_structure
   terraform/advanced_features


******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
