.. _CFNgin cfn lookup:

###
cfn
###

.. important::
  The Stack must exist in CloudFormation before the config using this Lookup begins processing to successfully get a value.
  This means that it must have been deployed using another Runway module, deployed from a config that is run before the one using it, deployed manually, or deployed in the same config using :attr:`~cfngin.stack.required`/:attr:`~cfngin.stack.required_by` to specify a dependency between the Stacks.


:Query Syntax: ``<stack-name>.<output-name>[::<arg>=<arg-val>, ...]``


Retrieve a value from CloudFormation Stack Outputs.

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

  namespace: example

  stacks:
    - ...
      variables:
        VpcId: ${cfn ${namespace}-vpc.Id}

Given the above config file, the lookup will get the value of the Output named **Id** from Stack **example-vpc**.
