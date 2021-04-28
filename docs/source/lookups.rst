.. _Lookups:

#######
Lookups
#######

Runway Lookups allow the use of variables within the Runway config file. These
variables can then be passed along to :ref:`deployments <runway-deployment>`,
:ref:`modules <runway-module>` and :ref:`tests <runway-test>`.

The syntax for a lookup is ``${<lookup-name> <query>::<arg-key>=<arg-value>}``

+---------------------------+-------------------------------------------------+
| Component                 | Description                                     |
+===========================+=================================================+
| ``${``                    | Signifies the opening of the lookup.            |
+---------------------------+-------------------------------------------------+
| ``<lookup-name>``         | The name of the lookup you wish to use (e.g.    |
|                           | ``env``). This signifies the *source* of the    |
|                           | data to be retrieved by the lookup.             |
+---------------------------+-------------------------------------------------+
|                           | The separator between lookup name a query.      |
+---------------------------+-------------------------------------------------+
| ``<query>``               | The value the lookup will be looking for. (e.g. |
|                           | ``AWS_REGION``)                                 |
|                           | | When using a lookup on a dictionary/mapping,  |
|                           | like  for the `var`_ lookup, you can get nested |
|                           | values by providing the full path to the value. |
|                           | (e.g. ``ami.dev``}                              |
+---------------------------+-------------------------------------------------+
| ``::``                    | The separator between a query and optional      |
|                           | arguments.                                      |
+---------------------------+-------------------------------------------------+
| ``<arg-key>=<arg-value>`` | An argument passed to a lookup. Multiple        |
|                           | arguments can be passed to a lookup by          |
|                           | separating them with a comma (``,``). Arguments |
|                           | are optional. Supported arguments depend on the |
|                           | lookup being used.                              |
+---------------------------+-------------------------------------------------+

Lookups can be nested (e.g. ``${var ami_id.${var AWS_REGION}}``).

Lookups can't resolve other lookups. For example, if i use ``${var region}`` in
my Runway config file to resolve the ``region`` from my variables file, the
value in the variables file can't be ``${env AWS_REGION}``. Well, it can but
it will resolve to the literal value provided, not an AWS region like you may
expect.

.. automodule:: runway.lookups.handlers.base


.. _cfn lookup:
.. _cfn-lookup:

***
cfn
***

.. important::
  The Stack must exist in CloudFormation before the module using this Lookup begins processing to successfully get a value.
  This means that the Stack must have been deployed by another module, run before the one using this Lookup, or it must have been created external to Runway.

Retrieve a value from CloudFormation Stack Outputs.

The query syntax for this lookup is ``<stack-name>.<output-name>``.
When specifying the output name, be sure to use the *Logical ID* of the output; not the *Export.Name*.

If the Lookup is unable to find a CloudFormation Stack Output matching the provided query, the default value is returned or an exception is raised to show why the value could be be resolved (e.g. Stack does not exist or output does not exist on the Stack).

.. seealso::
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
        path: sampleapp.tf
        options:
          terraform_backend_config:
            bucket: ${cfn common-tf-state.TerraformStateBucketName::region=us-east-1}
            dynamodb_table: ${cfn common-tf-state.TerraformStateTableName::region=us-east-1}
            region: us-east-1


.. _ecr lookup:
.. _ecr-lookup:

***
ecr
***

.. automodule:: runway.lookups.handlers.ecr
  :noindex:


.. _env lookup:
.. _env-lookup:

***
env
***

.. automodule:: runway.lookups.handlers.env


.. _ssm lookup:
.. _ssm-lookup:

***
ssm
***

Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query, the default value is returned or ``ParameterNotFound`` is raised if a default value is not provided.

Parameters of type ``SecureString`` are automatically decrypted.

Parameters of type ``StringList`` are returned as a list.

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.

.. rubric:: Example
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


.. _var lookup:
.. _var-lookup:

***
var
***

.. automodule:: runway.lookups.handlers.var
