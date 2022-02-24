.. _ssm lookup:
.. _ssm-lookup:

###
ssm
###

:Query Syntax: ``<parameter>[::<arg>=<arg-val>, ...]``


Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query, the default value is returned or :exc:`ParameterNotFound` is raised if a default value is not provided.

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

  deployment:
    - modules:
      - path: sampleapp.cfn
        parameters:
          secret_value: ${ssm /example/secret}
          conf_file: ${ssm /example/config/json::load=json, get=value}
          toggle: ${ssm toggle::load=yaml, get=val, transform=bool}
      env_vars:
        SOME_VARIABLE: ${ssm /example/param::region=us-east-1}
        DEFAULT_VARIABLE: ${ssm /example/default::default=default}
