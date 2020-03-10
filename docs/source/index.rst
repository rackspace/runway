Runway documentation
==================================

What is Runway?
^^^^^^^^^^^^^^^
Runway is a lightweight wrapper around infrastructure deployment (e.g.
CloudFormation, Terraform, Serverless) & linting (e.g. yamllint) tools to ease
management of per-environment configs & deployment.

Why use Runway?
^^^^^^^^^^^^^^^
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
   :caption: Contents:

   installation
   getting_started
   quickstart/index
   commands
   runway_config
   module_configuration/index
   cfngin/index
   lookups
   defining_tests
   repo_structure
   terminology
   apidocs/index
   developers/index
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
