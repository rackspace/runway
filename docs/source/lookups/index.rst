.. _Lookups:

#######
Lookups
#######

Runway Lookups allow the use of variables within the Runway config file.
These variables can then be passed along to :ref:`Deployment <runway_config:Deployment>`, :ref:`Modules <runway_config:Module>` and :ref:`tests <runway_config:Test>`.

The syntax for a lookup is ``${<lookup-name> <query>::<arg>=<arg-val>}``.

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
|                           |  like  for the :ref:`var lookup`,               |
|                           || you can get nested values by providing the     |
|                           |  full path to the value (e.g. ``ami.dev``).     |
+---------------------------+-------------------------------------------------+
| ``::``                    | The separator between a query and optional      |
|                           | arguments.                                      |
+---------------------------+-------------------------------------------------+
| ``<arg>=<arg-val>``       || An argument passed to a lookup.                |
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



****************
Built-in Lookups
****************

.. toctree::
  :maxdepth: 1
  :glob:

  **
