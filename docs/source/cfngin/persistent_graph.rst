.. _cfngin_persistent_graph:

################
Persistent Graph
################

Each time Runway's CFNgin is run, it creates a dependency :term:`graph` of :class:`stacks <cfngin.stack>`.
This is used to determine the order in which to execute them.
This :term:`graph` can be persisted between runs to track the removal of :class:`stacks <cfngin.stack>` from the config file.

When a |Stack| is present in the persistent graph but not in the :term:`graph` constructed from the config file, CFNgin will delete the Stack from CloudFormation.
This takes effect when running either the :ref:`deploy command <command-deploy>` or :ref:`destroy command <command-destroy>`.

To enable persistent graph, define the :attr:`~cfngin.config.persistent_graph_key` field as a unique value that will be used to construct the path to the persistent graph object in S3.
This object is stored in the |cfngin_bucket| which is also used for CloudFormation templates.
The fully qualified path to the object will look like the below.

.. code-block:: shell

  s3://${cfngin_bucket}/${namespace}/persistent_graphs/${namespace}/${persistent_graph_key}.json


.. note::
  It is recommended to enable versioning on the |cfngin_bucket| when using persistent graph to have a backup version in the event something unintended happens.
  A warning will be logged if this is not enabled.

  If CFNgin creates a |cfngin_bucket| for you when persistent graph is enabled, it will be created with versioning enabled.

.. important::
  When choosing a value for :attr:`~cfngin.config.persistent_graph_key`, it is vital to ensure the value is unique for the |namespace| being used.
  If the key is a duplicate, Stacks that are not intended to be destroyed will be destroyed.


When executing an action that will be modifying the persistent graph (deploy or destroy), the S3 object is *"locked"*.
The lock is a tag applied to the object at the start of one of these actions.
The tag-key is **cfngin_lock_code** and the tag-value is UUID generated each time a config is processed.

To lock a persistent graph object, the tag must not be present on the object.
For CFNgin to act on the :term:`graph` (modify or unlock) the value of the tag must match the UUID of the current CFNgin session.
If the object is locked or the code does not match, an error will be raised and no action will be taken.
This prevents two parties from acting on the same persistent graph object concurrently which would create a race condition.

.. note::
  A persistent graph object can be unlocked manually by removing the **cfngin_lock_code** tag from it.
  This should be done with caution as it will cause any active sessions to raise an error.

.. rubric:: Example
.. code-block:: yaml
  :caption: configuration file

  namespace: example
  cfngin_bucket: cfngin-bucket
  persistent_graph_key: my_graph  # .json - will be appended if not provided
  stacks:
    - name: first_stack:
      ...
    - name: new_stack:
      ...

.. code-block:: json
  :caption: s3://cfngin-bucket/persistent_graphs/example/my_graph.json

  {
    "first_stack": [],
    "removed_stack": [
      "first_stack"
    ]
  }

Given the above config file and persistent graph, when running ``runway deploy``, the following will occur.

#. The ``{"Key": "cfngin_lock_code", "Value": "123456"}`` tag is applied to **s3://cfngin-bucket/persistent_graphs/example/my_graph.json** to lock it to the current session.

#. **removed_stack** is deleted from CloudFormation and deleted from the persistent graph object in S3.

#. **first_stack** is updated in CloudFormation and updated in the persistent graph object in S3 (incase dependencies change).

#. **new_stack** is created in CloudFormation and added to the persistent graph object in S3.

#. The ``{"Key": "cfngin_lock_code", "Value": "123456"}`` tag is removed from **s3://cfngin-bucket/persistent_graphs/example/my_graph.json** to unlock it for use in other sessions.
