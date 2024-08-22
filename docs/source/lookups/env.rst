.. _env lookup:
.. _env-lookup:

###
env
###

:Query Syntax: ``<variable-name>[::<arg>=<arg-val>, ...]``


Retrieve a value from an environment variable.

The value is retrieved from a copy of the current environment variables that is saved to the context object.
These environment variables are manipulated at runtime by Runway to fill in additional values such as ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the current execution.


.. note::
  ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` can only be resolved during the processing of a module.
  To ensure no error occurs when trying to resolve one of these in a :ref:`Deployment <runway_config:Deployment>` definition, provide a default value.


If the Lookup is unable to find an environment variable matching the provided query, the default value is returned or a :exc:`ValueError` is raised if a default value was not provided.


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
            creator: ${env USER}
      env_vars:
        ENVIRONMENT: ${env DEPLOY_ENVIRONMENT::default=default}
