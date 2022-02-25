.. _output lookup:

######
output
######

:Query Syntax: ``<relative-stack-name>.<output-name>[::<arg>=<arg-val>, ...]``


The output_ lookup retrieves an Output from the given Stack name within the current |namespace|.

CFNgin treats output lookups differently than other lookups by auto adding the referenced stack in the lookup as a requirement to the stack whose variable the output value is being passed to.


.. versionchanged:: 2.7.0
  The ``<relative-stack-name>::<output-name>`` syntax is deprecated to comply with Runway's lookup syntax.



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region



*******
Example
*******

You can specify an output lookup with the following syntax:

.. code-block:: yaml

  namespace: example

  stacks:
    - ...
      variables:
        ConfVariable: ${output stack-name.OutputName}
