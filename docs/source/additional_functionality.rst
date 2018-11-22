Addtional Functionality
=======================

whichenv
^^^^^^^^
Execute ``runway whichenv`` to output the name of the currently detected environment 
(see `Basic Concepts <basic_concepts.html#environments>`_ for an overview of how runway determines the environment name).

gen-sample
^^^^^^^^^^
Execute ``runway gen-sample`` followed by a module type to create a sample module directory, containing example 
files appropriate for the module type:

- ``runway gen-sample cfn``: Creates a sample CloudFormation module in ``sampleapp.cfn``
- ``runway gen-sample sls``: Creates a sample Serverless Framework module in ``sampleapp.sls``
- ``runway gen-sample stacker``: Creates a sample CloudFormation module (with Python templates using Troposphere and awacs) in ``runway-sample-tfstate.cfn``
- ``runway gen-sample tf``: Creates a sample Terraform module in ``sampleapp.tf``
