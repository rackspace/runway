.. _cfn lookup:
.. _cfn-lookup:

###
cfn
###

.. important::
  The Stack must exist in CloudFormation before the module using this Lookup begins processing to successfully get a value.
  This means that the Stack must have been deployed by another module, run before the one using this Lookup, or it must have been created external to Runway.


:Query Syntax: ``<stack-name>.<output-name>[::<arg>=<arg-val>, ...]``


Retrieve a value from CloudFormation Stack Outputs.

The query syntax for this lookup is ``<stack-name>.<output-name>``.
When specifying the output name, be sure to use the *Logical ID* of the output; not the *Export.Name*.

If the Lookup is unable to find a CloudFormation Stack Output matching the provided query, the default value is returned or an exception is raised to show why the value could be be resolved (e.g. Stack does not exist or output does not exist on the Stack).


.. versionadded:: 1.11.0


.. seealso::
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments`.



*******
Example
*******

.. code-block:: yaml

  deployments:
    - modules:
        path: sampleapp.tf
        options:
          terraform_backend_config:
            bucket: ${cfn common-tf-state.TerraformStateBucketName::region=us-east-1}
            dynamodb_table: ${cfn common-tf-state.TerraformStateTableName::region=us-east-1}
            region: us-east-1
