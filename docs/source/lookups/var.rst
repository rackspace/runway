.. _var lookup:
.. _var-lookup:

###
var
###

:Query Syntax: ``<variable-name>[::<arg>=<arg-val>, ...]``


Retrieve a variable from the variables file or definition.

If the Lookup is unable to find an defined variable matching the provided query, the default value is returned or a ``ValueError`` is raised if a default value was not provided.

Nested values can be used by providing the full path to the value but, it will not select a list element.

The returned value can contain any YAML support data type (dictionaries/mappings/hashes, lists/arrays/sequences, strings, numbers, and boolean).


.. versionadded:: 1.4.0



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region



*******
Example
*******

.. code-block:: yaml

  deployment:
    - modules:
        - path: sampleapp.cfn
          parameters:
            ami_id: ${var ami_id.${env AWS_REGION}}
      env_vars:
        SOME_VARIABLE: ${var some_variable::default=default}
