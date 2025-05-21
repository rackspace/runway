######################
Upgrading to Runway v3
######################

.. important::
  Each upgrade guide is written with the assumption that you are upgrading from the previous major release.
  If this is not the case, some information maybe missing or incorrect.

The goal of this guide is to provide information about breaking changes contained in a major release.
This guid does not provide a comprehensive list of all changes.
For a full list of changes please refer to the :ref:`changelog:CHANGELOG`.


****************
Behavior Changes
****************


************
Deprecations
************


********
Removals
********

- ``aws_lambda.upload_lambda_functions`` CFNgin hook
  - :ref:`cfngin/hooks/awslambda.PythonFunction:How To Migrate From runway.cfngin.hooks.aws_lambda.upload_lambda_functions`
