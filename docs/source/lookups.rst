.. _Lookups:

#######
Lookups
#######

Runway Lookups allow the use of variables within the Runway config file.
These variables can then be passed along to :ref:`deployments <runway-deployment>`, :ref:`modules <runway-module>` and :ref:`tests <runway-test>`.

The syntax for a lookup is ``${<lookup-name> <query>::<arg-key>=<arg-value>}``.

+---------------------------+-------------------------------------------------+
| Component                 | Description                                     |
+===========================+=================================================+
| ``${``                    | Signifies the opening of the lookup.            |
+---------------------------+-------------------------------------------------+
| ``<lookup-name>``         || The name of the lookup you wish to use         |
|                           |  (e.g. ``env``).                                |
|                           || This signifies the *source* of the data to     |
|                           | be retrieved by the lookup.                     |
+---------------------------+-------------------------------------------------+
|                           | The separator between lookup name a query.      |
+---------------------------+-------------------------------------------------+
| ``<query>``               || The value the lookup will be looking for       |
|                           |  (e.g. ``AWS_REGION``).                         |
|                           || When using a lookup on a dictionary/mapping,   |
|                           |  like  for the `var`_ lookup,                   |
|                           || you can get nested values by providing the     |
|                           |  full path to the value (e.g. ``ami.dev``).     |
+---------------------------+-------------------------------------------------+
| ``::``                    | The separator between a query and optional      |
|                           | arguments.                                      |
+---------------------------+-------------------------------------------------+
| ``<arg-key>=<arg-value>`` || An argument passed to a lookup.                |
|                           || Multiple arguments can be passed to a lookup   |
|                           |  by separating them with a                      |
|                           || comma (``,``).                                 |
|                           || Arguments are optional.                        |
|                           || Supported arguments depend on the lookup being |
|                           |  used.                                          |
+---------------------------+-------------------------------------------------+

Lookups can be nested (e.g. ``${var ami_id.${var AWS_REGION}}``).

Lookups can't resolve other lookups.
For example, if i use ``${var region}`` in my Runway config file to resolve the ``region`` from my variables file, the value in the variables file can't be ``${env AWS_REGION}``.
Well, it can but it will resolve to the literal value provided, not an AWS region like you may expect.


.. contents::
  :depth: 4


.. _lookup arguments:

****************
Lookup Arguments
****************

Arguments can be passed to Lookups to effect how they function.

To provide arguments to a Lookup, use a double-colon (``::``) after the query.
Each argument is then defined as a **key** and **value** separated with equals (``=``) and the arguments themselves are separated with a comma (``,``).
The arguments can have an optional space after the comma and before the next key to make them easier to read but this is not required.
The value of all arguments are read as strings.

.. rubric:: Example
.. code-block:: yaml

    ${var my_query::default=true, transform=bool}
    ${env MY_QUERY::default=1,transform=bool}

Each Lookup may have their own, specific arguments that it uses to modify its functionality or the value it returns.
There is also a common set of arguments that all Lookups accept.

.. _Common Lookup Arguments:

Common Lookup Arguments
=======================

.. data:: default
  :type: Any
  :noindex:

  If the Lookup is unable to find a value for the provided query, this value will be returned instead of raising an exception.

.. data:: get
  :type: str
  :noindex:

  Can be used on a dictionary type object to retrieve a specific piece of data.
  This is executed after the optional ``load`` step.

.. data:: indent
  :type: int
  :noindex:

  Number of spaces to use per indent level when transforming a dictionary type object to a string.

.. data:: load
  :type: Literal["json", "troposphere", "yaml"]
  :noindex:

  Load the data to be processed by a Lookup using a specific parser.
  This is the first action taking on the data after it has been retrieved from it's source.
  The data must be in a format that is supported by the parser in order for it to be used.

  **json**
    Loads a JSON serializable string into a dictionary like object.
  **troposphere**
    Loads the ``properties`` of a subclass of ``troposphere.BaseAWSObject`` into a dictionary.
  **yaml**
    Loads a YAML serializable string into a dictionary like object.

.. data:: region
  :type: str
  :noindex:

  AWS region used when creating a ``boto3.Session`` to retrieve data.
  If not provided, the region currently being processed will be used.
  This can be specified to always get data from one region regardless of region is being deployed to.

.. data:: transform
  :type: Literal["bool", "str"]
  :noindex:

  Transform the data that will be returned by a Lookup into a different data type.
  This is the last action taking on the data before it is returned.

  Supports the following:

  **bool**
    Converts a string or boolean value into a boolean.

  **str**
    Converts any value to a string. The original data type determines the end result.

    ``list``, ``set``, and ``tuple`` will become a comma delimited list

    ``dict`` and anything else will become an escaped JSON string.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - parameters:
        some_variable: ${var some_value::default=my_value}
        comma_list: ${var my_list::default=undefined, transform=str}


----


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

.. versionadded:: 1.11.0


----


.. _ecr lookup:
.. _ecr-lookup:

***
ecr
***

Retrieve a value from AWS Elastic Container Registry (ECR).

This Lookup only supports very specific queries.

.. versionadded:: 1.18.0

Supported Queries
=================

login-password
--------------

Get a password to login to ECR registry.

The returned value can be passed to the login command of the container client of your preference, such as the :ref:`Docker CFNgin hook <cfngin.hooks.docker>`.
After you have authenticated to an Amazon ECR registry with this Lookup, you can use the client to push and pull images from that registry as long as your IAM principal has access to do so until the token expires.
The authorization token is valid for **12 hours**.

.. rubric:: Arguments

This Lookup does not support any arguments.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - modules:
      - path: example.cfn
        parameters:
          ecr_password: ${ecr login-password}
    ...


----


.. _env lookup:
.. _env-lookup:

***
env
***

Retrieve a value from an environment variable.

The value is retrieved from a copy of the current environment variables that is saved to the context object.
These environment variables are manipulated at runtime by Runway to fill in additional values such as ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the current execution.

.. note::
  ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` can only be resolved during the processing of a module.
  To ensure no error occurs when trying to resolve one of these in a :ref:`Deployment <runway-deployment>` definition, provide a default value.

If the Lookup is unable to find an environment variable matching the provided query, the default value is returned or a :exc:`ValueError` is raised if a default value was not provided.


.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region


.. rubric:: Example
.. code-block:: yaml

  deployment:
    - modules:
        - path: sampleapp.cfn
          parameters:
            creator: ${env USER}
      env_vars:
        ENVIRONMENT: ${env DEPLOY_ENVIRONMENT::default=default}

.. versionadded:: 1.4.0


----


.. _ssm lookup:
.. _ssm-lookup:

***
ssm
***

Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query, the default value is returned or :exc:`ParameterNotFound` is raised if a default value is not provided.

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

.. versionadded:: 1.5.0


----


.. _var lookup:
.. _var-lookup:

***
var
***

Retrieve a variable from the variables file or definition.

If the Lookup is unable to find an defined variable matching the provided query, the default value is returned or a ``ValueError`` is raised if a default value was not provided.

Nested values can be used by providing the full path to the value but, it will not select a list element.

The returned value can contain any YAML support data type (dictionaries/mappings/hashes, lists/arrays/sequences, strings, numbers, and boolean).


.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region


.. rubric:: Example
.. code-block:: yaml

  deployment:
    - modules:
        - path: sampleapp.cfn
          parameters:
            ami_id: ${var ami_id.${env AWS_REGION}}
      env_vars:
        SOME_VARIABLE: ${var some_variable::default=default}

.. versionadded:: 1.4.0
