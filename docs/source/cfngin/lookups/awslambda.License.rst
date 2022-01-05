.. _AWS::Lambda::LayerVersion.License: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-layerversion.html#cfn-lambda-layerversion-license

#################
awslambda.License
#################

:Query Syntax: ``<hook.data_key>``


.. automodule:: runway.cfngin.lookups.handlers.awslambda
  :exclude-members: AwsLambdaLookup
  :noindex:


A string or ``None`` is returned by this lookup.
The returned value can be passed directly to `AWS::Lambda::LayerVersion.License`_.


.. versionadded:: 2.5.0



*******
Example
*******

.. code-block:: yaml

  namespace: example
  cfngin_bucket: ''
  sys_path: ./

  pre_deploy:
    - path: runway.cfngin.hooks.awslambda.PythonLayer
      data_key: example-layer-01
      args:
        ...
    - path: runway.cfngin.hooks.awslambda.PythonLayer
      data_key: example-layer-02
      args:
        ...

  stacks:
    - name: example-stack-01
      class_path: blueprints.FooStack
      variables:
        License: ${awslambda.License example-layer-01}
        ...
    - name: example-stack-02
      template_path: ./templates/bar-stack.yml
      variables:
        License: ${awslambda.License example-layer-02}
        ...
