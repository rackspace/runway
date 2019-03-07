runway documentation
==================================

What is runway?
^^^^^^^^^^^^^^^
Runway is a lightweight wrapper around linting (e.g. yamllint) & infrastructure deployment tools 
(e.g. CloudFormation, Terraform, Serverless) to ease management of per-environment configs 
& deployment.

Why use runway?
^^^^^^^^^^^^^^^
Very simple configuration to:

- Perform automatic linting/verification
- Ensure deployments are only performed when an environment config is present
- Define an IAM role to assume for each deployment
- Wrangle Terraform backend/workspace configs w/ per-environment tfvars
- Avoid long-term tool lock-in
    + runway is a simple wrapper around standard tools. It simply helps to avoid convoluted Makefiles / CI jobs

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   basic_concepts
   installation
   how_to_use
   repo_structure
   runway_config
   module_configuration
   additional_functionality
   quickstart
   staticsite_config
   developers
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
