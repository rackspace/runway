######
Runway
######

Runway is a lightweight wrapper around infrastructure deployment (e.g. CloudFormation, Terraform, Serverless) & linting (e.g. yamllint) tools to ease management of per-environment configs & deployment.

.. image:: images/runway-example.gif
  :align: center
  :alt: runway-example.gif

.. toctree::
  :caption: Runway
  :maxdepth: 2
  :hidden:

  installation
  upgrades
  getting_started
  quickstart/index
  commands
  runway_config
  lookups/index
  defining_tests
  repo_structure


----

********************
Module Configuration
********************


AWS Cloud Development Kit (CDK)
===============================

The CDK module type is deployed using the `AWS Cloud Development Kit (CDK) <https://docs.aws.amazon.com/cdk/latest/guide/home.html>`__.
Runway uses `system installed npm <https://www.npmjs.com/get-npm>`__ to install the CDK per-module.
This means that the CDK must be included as a dev dependency in the **package.json** of the module.

- :ref:`Configuration <cdk-configuration>`
- :ref:`Directory Structure <cdk-directory-structure>`
- :ref:`Advanced Features <cdk-advanced-features>`

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

- :ref:`Configuration <cfngin-configuration>`
- :ref:`Directory Structure <cfngin-directory-structure>`
- :ref:`Advanced Features <cfngin-advanced-features>`

.. toctree::
  :caption: CloudFormation & Troposphere
  :maxdepth: 2
  :hidden:

  cfngin/configuration
  cfngin/directory_structure
  cfngin/advanced_features
  cfngin/migrating

.. _Troposphere: https://github.com/cloudtools/troposphere


Kubernetes
==========

Kubernetes manifests can be deployed via Runway offering an ideal way to handle core infrastructure-layer (e.g. shared ConfigMaps & Service Accounts) configuration of clusters by using `Kustomize overlays <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays>`__.

- :ref:`Configuration <k8s-configuration>`
- :ref:`Directory Structure <k8s-directory-structure>`
- :ref:`Examples <k8s-examples>`
- :ref:`Advanced Features <k8s-advanced-features>`

.. toctree::
  :caption: Kubernetes
  :maxdepth: 2
  :hidden:

  kubernetes/configuration
  kubernetes/directory_structure
  kubernetes/examples
  kubernetes/advanced_features


Serverless Framework
====================

The Serverless module type is deployed using the `Serverless Framework <https://serverless.com>`__.
Runway uses `system installed npm <https://www.npmjs.com/get-npm>`__ to install Serverless per-module.
This means that Serverless must be included as a dev dependency in the **package.json** of the module.

- :ref:`Configuration <sls-configuration>`
- :ref:`Directory Structure <sls-directory-structure>`
- :ref:`Advanced Features <sls-advanced-features>`

.. toctree::
  :caption: Serverless Framework
  :maxdepth: 2
  :hidden:

  serverless/configuration
  serverless/directory_structure
  serverless/advanced_features


Static Site
===========

This module type performs idempotent deployments of static websites.
It combines CloudFormation stacks (for S3 buckets & CloudFront Distribution) with additional logic to build & sync the sites.

A start-to-finish example walkthrough is available in the :ref:`Conduit quickstart<qs-conduit>`.

.. note::
  The CloudFront Distribution that is created by default can take a significant amount of time to spin up on initial deploy (5 to 60 minutes is not abnormal).
  Incorporating CloudFront with a static site is a common best practice, however, if you are working on a development project it may benefit you to add the :ref:`staticsite_cf_disable <staticsite_cf_disable>` parameter.

- :ref:`Configuration <staticsite-configuration>`
- :ref:`Directory Structure <staticsite-directory-structure>`
- :ref:`Examples <staticsite-examples>`
- :ref:`Advanced Features <staticsite-advanced-features>`

.. toctree::
  :caption: Static Site
  :maxdepth: 2
  :hidden:

  staticsite/configuration
  staticsite/directory_structure
  staticsite/examples
  staticsite/advanced_features


Terraform
=========

Runway provides a simple way to run the Terraform versions you want with variable values specific to each environment.
Terraform does not need to be installed prior to using this module type.
Runway maintains a cache of Terraform versions on a system, downloading and installing different versions as needed.

- :ref:`Configuration <tf-configuration>`
- :ref:`Directory Structure <tf-directory-structure>`
- :ref:`Advanced Features <tf-advanced-features>`

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

  changelog
  License <license>
  terminology
