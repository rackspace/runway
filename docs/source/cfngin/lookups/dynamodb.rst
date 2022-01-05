########
dynamodb
########

:Query Syntax: ``<region>:<table-name>@<partition-key>:<value>.<attribute>``


The dynamodb_ lookup type retrieves a value from a DynamoDb table.

As an example, if you have a Dynamo Table named ``TestTable`` and it has an Item with a Primary Partition key called ``TestKey`` and a value named ``BucketName``, you can look it up by using CFNgin.
The lookup key in this case is TestVal



*******
Example
*******

.. code-block:: yaml

  # We can reference that dynamo value
  BucketName: ${dynamodb us-east-1:TestTable@TestKey:TestVal.BucketName}

  # Which would resolve to:
  BucketName: test-bucket

You can lookup other data types by putting the data type in the lookup.
Valid values are ``S`` (String), ``N`` (Number), ``M`` (Map), ``L`` (List).

.. code-block:: yaml

  ServerCount: ${dynamodb us-east-1:TestTable@TestKey:TestVal.ServerCount[N]}

This would return an int value, rather than a string

You can lookup values inside of a map.

.. code-block:: yaml

  ServerCount: ${dynamodb us-east-1:TestTable@TestKey:TestVal.ServerInfo[M].ServerCount[N]}
