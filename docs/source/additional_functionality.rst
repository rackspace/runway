Addtional Functionality
=======================

whichenv
^^^^^^^^
Execute ``runway whichenv`` to output the name of the currently detected environment 
(see `Basic Concepts <basic_concepts.html#environments>`_ for an overview of how runway determines the environment name).

Static Website Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^
Runway comes pre-packaged with a module plugin for performing idempotent deployments of static websites.
It combines CloudFormation stacks (for S3 buckets & CloudFront Distribution) with additional logic to build & sync the sites.

It can be used with a configuration like the following::

    deployments:
      - modules:
          - path: web
            class_path: runway.module.staticsite.StaticSite
            environments:
              dev:
                namespace: contoso-dev
                staticsite_acmcert_arn: arn:aws:acm:us-east-1:123456789012:certificate/...
            options:
              build_steps:
                - npm ci
                - npm run build
              build_output: dist
        regions:
          - us-west-2

This will build the website in ``web`` via the specified build_steps and then upload the contents of ``web/dist`` 
to a S3 bucket created in the CloudFormation stack ``web-dev-conduit``. On subsequent deploys, the website will 
be built and synced only if the (non-git-ignored) files in ``web`` change.

The site domain name is available via the ``CFDistributionDomainName`` output of the ``<namespace>-<path>`` stack 
(e.g. ``contoso-dev-web`` above) and will be displayed on stack creation/updates.

See additional options here [LINK TO STATICSITE], or a start-to-finish example walkthrough here [LINK TO CONDUIT].

gen-sample
^^^^^^^^^^
Execute ``runway gen-sample`` followed by a module type to create a sample module directory, containing example 
files appropriate for the module type:

- ``runway gen-sample cfn``: Creates a sample CloudFormation module in ``sampleapp.cfn``
- ``runway gen-sample sls``: Creates a sample Serverless Framework module in ``sampleapp.sls``
- ``runway gen-sample stacker``: Creates a sample CloudFormation module (with Python templates using Troposphere and awacs) in ``runway-sample-tfstate.cfn``
- ``runway gen-sample tf``: Creates a sample Terraform module in ``sampleapp.tf``