.. _CFNgin env lookup:

###
env
###

:Query Syntax: ``<variable-name>[::<arg>=<arg-val>, ...]``


Retrieve a value from an environment variable.

The value is retrieved from a copy of the current environment variables that is saved to the context object.
These environment variables are manipulated at runtime by Runway to fill in additional values such as ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the current execution.

If the Lookup is unable to find an environment variable matching the provided query, the default value is returned or a :exc:`ValueError` is raised if a default value was not provided.


.. here, versionadded refers to when it was added to the CFNgin registry
.. versionadded:: 2.7.0



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region



*******
Example
*******

.. code-block:: yaml

  stacks:
    - ...
      variables:
        Foo: ${env bar::default=foobar}
