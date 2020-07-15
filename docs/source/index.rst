####################
Runway Documentation
####################

.. image:: images/runway-example.gif
   :align: center
   :alt: runway-example.gif

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
   :caption: Runway
   :maxdepth: 2
   :hidden:

   installation
   getting_started
   quickstart/index
   commands
   runway_config
   lookups
   defining_tests
   repo_structure


----

.. _module-configurations:

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


.. _mod-cfn:

CloudFormation & Troposphere
============================

The CloudFormation module type is deployed using Runway's CloudFormation engine (CFNgin).
It is able to deploy raw CloudFormation templates (JSON & YAML) and Troposphere_ templates that are written in the form of a :ref:`Blueprint`.

- `Configuration <cfngin/configuration.html>`__
- `Directory Structure <cfngin/directory_structure.html>`__
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


.. _mod-k8s:

Kubernetes
==========

Kubernetes manifests can be deployed via Runway offering an ideal way to handle core infrastructure-layer (e.g. shared ConfigMaps & Service Accounts) configuration of clusters by using `Kustomize overlays <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays>`__.

- `Configuration <kubernetes/configuration.html>`__
- `Directory Structure <kubernetes/directory_structure.html>`__
- `Examples <kubernetes/examples.html>`__
- `Advanced Features <kubernetes/advanced_features.html>`__

.. toctree::
   :caption: Kubernetes
   :maxdepth: 2
   :hidden:

   kubernetes/configuration
   kubernetes/directory_structure
   kubernetes/examples
   kubernetes/advanced_features


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


.. _mod-staticsite:

Static Site
===========

This module type performs idempotent deployments of static websites.
It combines CloudFormation stacks (for S3 buckets & CloudFront Distribution) with additional logic to build & sync the sites.

A start-to-finish example walkthrough is available in the :ref:`Conduit quickstart<qs-conduit>`.

.. note::
  The CloudFront Distribution that is created by default can take a significant amount of time to spin up on initial deploy (5 to 60 minutes is not abnormal).
  Incorporating CloudFront with a static site is a common best practice, however, if you are working on a development project it may benefit you to add the :ref:`staticsite_cf_disable <staticsite_cf_disable>` parameter.

- `Configuration <staticsite/configuration.html>`__
- `Directory Structure <staticsite/directory_structure.html>`__
- `Examples <staticsite/examples.html>`__
- `Advanced Features <staticsite/advanced_features.html>`__

.. toctree::
   :caption: Static Site
   :maxdepth: 2
   :hidden:

   staticsite/configuration
   staticsite/directory_structure
   staticsite/examples
   staticsite/advanced_features


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


----


.. toctree::
   :caption: Developers Guide
   :maxdepth: 2
   :glob:
   :hidden:

   apidocs/index
   developers/*

.. toctree::
   :caption: Maintainers Guide
   :maxdepth: 2
   :glob:
   :hidden:

   maintainers/*

.. toctree::
   :caption: Additional Information
   :maxdepth: 2
   :hidden:

   License <license>
   terminology



******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
