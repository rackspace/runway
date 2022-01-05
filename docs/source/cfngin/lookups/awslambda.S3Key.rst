.. _AWS::Lambda::Function.Code.S3Key: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-function-code.html#cfn-lambda-function-code-s3key
.. _AWS::Lambda::LayerVersion.Content.S3Key: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-layerversion-content.html#cfn-lambda-layerversion-content-s3key

###############
awslambda.S3Key
###############

:Query Syntax: ``<hook.data_key>``


.. automodule:: runway.cfngin.lookups.handlers.awslambda
  :exclude-members: AwsLambdaLookup
  :noindex:


A string is returned by this lookup.
The returned value can be passed directly to `AWS::Lambda::Function.Code.S3Key`_ or `AWS::Lambda::LayerVersion.Content.S3Key`_.


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
        S3Key: ${awslambda.S3Key example-function-01}
        ...
    - name: example-stack-02
      template_path: ./templates/bar-stack.yml
      variables:
        S3Key: ${awslambda.S3Key example-function-02}
        ...
