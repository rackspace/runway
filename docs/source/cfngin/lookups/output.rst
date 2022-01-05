.. _output lookup:

######
output
######

:Query Syntax: ``<stack-name>::<output-name>``


The output_ lookup retrieves an Output from the given Stack name within the current |namespace|.

CFNgin treats output lookups differently than other lookups by auto adding the referenced stack in the lookup as a requirement to the stack whose variable the output value is being passed to.



*******
Example
*******

You can specify an output lookup with the following syntax:

.. code-block:: yaml

  ConfVariable: ${output someStack::SomeOutput}
