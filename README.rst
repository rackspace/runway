Runway
======

What?
-----

A lightweight wrapper around linting (e.g. yamllint) & infrastructure
deployment tools (e.g. CloudFormation, Terraform, Serverless) to ease
management of per-environment configs & deployment.

Why?
----

Very simple configuration to:

-  Perform automatic linting/verification
-  Ensure deployments are only performed when an environment config is
   present
-  Define an IAM role to assume for each deployment
-  Wrangle Terraform backend/workspace configs w/ per-environment tfvars
-  Avoid long-term tool lock-in

   -  Runway is a simple wrapper around standard tools. It simply helps
      to avoid convoluted Makefiles/CI jobs and encourage best practices

How?
----

See the `doc site <https://docs.onica.com/projects/runway>`__.

Complete quickstart documentation, including Docker images,
CloudFormation templates, and walkthrough can be found
`here <https://docs.onica.com/projects/runway/en/latest/quickstart.html>`__
