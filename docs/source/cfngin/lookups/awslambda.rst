#########
awslambda
#########

:Query Syntax: ``<hook.data_key>``


.. automodule:: runway.cfngin.lookups.handlers.awslambda
  :exclude-members: AwsLambdaLookup
  :noindex:


An :class:`~runway.cfngin.hooks.awslambda.models.responses.AwsLambdaHookDeployResponse` object is returned by this lookup.
It is recommended to only use this lookup when passing the value into a :class:`~runway.cfngin.blueprints.base.Blueprint` or hook as further processing will be required.


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
        code_metadata: ${awslambda example-function-01}
        ...
    - name: example-stack-02
      class_path: blueprints.BarStack
      variables:
        code_metadata: ${awslambda example-function-02}
        ...
