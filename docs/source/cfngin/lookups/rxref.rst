.. _rxref lookup:

#####
rxref
#####

:Query Syntax: ``<stack-name>::<output-name>``


The rxref_ lookup type is very similar to the :ref:`xref lookup` type.
Where the :ref:`xref lookup` type assumes you provided a fully qualified stack name, rxref_, like the :ref:`output lookup` expands and retrieves the output from the given Stack name within the current |namespace|, even if not defined in the CFNgin config you provided it.

Because there is no requirement to keep all stacks defined within the same CFNgin YAML config, you might need the ability to read outputs from other Stacks deployed by CFNgin into your same account under the same |namespace|.
rxref_ gives you that ability.
This is useful if you want to break up very large configs into smaller groupings.

Also, unlike the :ref:`output lookup` type, rxref_ doesn't impact Stack requirements.



*******
Example
*******

.. code-block:: yaml

  # in example-us-east-1.env
  namespace: MyNamespace

  # in cfngin.yaml
  ConfVariable: ${rxref my-stack::SomeOutput}

  # the above would effectively resolve to
  ConfVariable: ${xref MyNamespace-my-stack::SomeOutput}

Although possible, it is not recommended to use ``rxref`` for stacks defined within the same CFNgin YAML config.
