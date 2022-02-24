###
ssm
###

:Query Syntax: ``<parameter>[::<arg>=<arg-val>, ...]``


Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query, the default value is returned or ``ParameterNotFound`` is raised if a default value is not provided.

Parameters of type ``SecureString`` are automatically decrypted.

Parameters of type ``StringList`` are returned as a list.


.. versionadded:: 1.5.0



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments`.



*******
Example
*******

.. code-block:: yaml

  stacks:
    - ...
      variables:
        Example: ${ssm /example/secret}
