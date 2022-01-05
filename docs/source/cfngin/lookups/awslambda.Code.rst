##############
awslambda.Code
##############

:Query Syntax: ``<hook.data_key>``


.. automodule:: runway.cfngin.lookups.handlers.awslambda
  :exclude-members: AwsLambdaLookup
  :noindex:


A ``troposphere.awslambda.Code`` object is returned by this lookup.
It is recommended to only use this lookup when passing the value into a :class:`~runway.cfngin.blueprints.base.Blueprint` or hook as further processing will be required.
However, it can be passed directly in the ``Code`` keyword argument of ``troposphere.awslambda.Function``.


.. versionadded:: 2.5.0



*******
Example
*******

.. code-block:: yaml

  namespace: example
  cfngin_bucket: ''
  sys_path: ./

  pre_deploy:
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      data_key: example-function-01
      args:
        ...
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      data_key: example-function-02
      args:
        ...

  stacks:
    - name: example-stack-01
      class_path: blueprints.FooStack
      variables:
        code_object: ${awslambda.Code example-function-01}
        ...
    - name: example-stack-02
      class_path: blueprints.BarStack
      variables:
        code_object: ${awslambda.Code example-function-02}
        ...
