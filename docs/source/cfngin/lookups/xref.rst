.. _xref lookup:

####
xref
####

.. deprecated:: 1.11.0
  Replaced by :ref:`CFNgin cfn lookup`


:Query Syntax: ``<fully-qualified-stack-name>::<output-name>``


The xref_ lookup type is very similar to the :ref:`output lookup` type, the difference being that xref_ resolves output values from stacks that aren't contained within the current CFNgin |namespace|, but are existing Stacks containing outputs within the same region on the AWS account you are deploying into.
xref_ allows you to lookup these outputs from the Stacks already in your account by specifying the stacks fully qualified name in the CloudFormation console.

Where the :ref:`output lookup` type will take a Stack name and use the current context to expand the fully qualified stack name based on the |namespace|, xref_ skips this expansion because it assumes you've provided it with the fully qualified stack name already.
This allows you to reference output values from any CloudFormation Stack in the same region.

Also, unlike the :ref:`output lookup` type, xref_ doesn't impact stack requirements.



*******
Example
*******

.. code-block:: yaml

  ConfVariable: ${xref fully-qualified-stack::SomeOutput}
