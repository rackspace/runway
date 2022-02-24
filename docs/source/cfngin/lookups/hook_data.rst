.. _hook_data lookup:

#########
hook_data
#########

:Query Syntax: ``<hook.data_key>[::<arg>=<arg-val>, ...]``


When using hooks, you can have the hook store results in the :attr:`CfnginContext.hook_data <runway.context.CfnginContext.hook_data>` dictionary on the context by setting :attr:`~cfngin.hook.data_key` in the :class:`~cfngin.hook` config.

This lookup lets you look up values in that dictionary.
A good example of this is when you use the :ref:`aws_lambda hook` to upload AWS Lambda code, then need to pass that code object as the **Code** variable in a Blueprint.


.. versionchanged:: 2.0.0
  Support for the syntax deprecated in *1.5.0* has been removed.

.. versionchanged:: 1.5.0
  The ``<hook_name>::<key>`` syntax was deprecated with support being added for the ``key.nested_key`` syntax for accessing data within a dictionary.



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region



*******
Example
*******

.. code-block:: yaml

  # If you set the ``data_key`` config on the aws_lambda hook to be "myfunction"
  # and you name the function package "TheCode" you can get the troposphere
  # awslambda.Code object with:

  Code: ${hook_data myfunction.TheCode}

  # If you need to pass the code location as individual strings for use in a
  # CloudFormation template instead of a Blueprint, you can do so like this:

  Bucket: ${hook_data myfunction.TheCode::load=troposphere, get=S3Bucket}
  Key: ${hook_data myfunction.TheCode::load=troposphere, get=S3Key}
