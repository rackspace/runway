.. _rxref lookup:

#####
rxref
#####

:Query Syntax: ``<relative-stack-name>.<output-name>[::<arg>=<arg-val>, ...]``


The rxref_ lookup type is very similar to the :ref:`CFNgin cfn lookup` lookup type.
Where the :ref:`CFNgin cfn lookup` type assumes you provided a fully qualified stack name, rxref_, like the :ref:`output lookup` expands and retrieves the output from the given Stack name within the current |namespace|, even if not defined in the CFNgin config you provided it.

Because there is no requirement to keep all stacks defined within the same CFNgin YAML config, you might need the ability to read outputs from other Stacks deployed by CFNgin into your same account under the same |namespace|.
rxref_ gives you that ability.
This is useful if you want to break up very large configs into smaller groupings.

Also, unlike the :ref:`output lookup` type, rxref_ doesn't impact Stack requirements.


.. versionchanged:: 2.7.0
  The ``<relative-stack-name>::<output-name>`` syntax is deprecated to comply with Runway's lookup syntax.



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments`.



*******
Example
*******

.. code-block:: yaml

  namespace: namespace

  stacks:
    - ...
      variables:
        ConfVariable0: ${rxref my-stack.SomeOutput}
        # both of these lookups are functionally equivalent
        ConfVariable1: ${cfn namespace-my-stack.SomeOutput}


Although possible, it is not recommended to use ``rxref`` for stacks defined within the same CFNgin YAML config.
Doing so would require the use of :attr:`~cfngin.stack.required_by` or :attr:`~cfngin.stack.requires`.
