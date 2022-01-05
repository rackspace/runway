.. _AWS::Lambda::Version.CodeSha256: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-version.html#cfn-lambda-version-codesha256

####################
awslambda.CodeSha256
####################

:Query Syntax: ``<hook.data_key>``


.. automodule:: runway.cfngin.lookups.handlers.awslambda
  :exclude-members: AwsLambdaLookup
  :noindex:


A string is returned by this lookup.
The returned value can be passed directly to `AWS::Lambda::Version.CodeSha256`_.


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
        CodeSha256: ${awslambda.CodeSha256 example-function-01}
        ...
    - name: example-stack-02
      template_path: ./templates/bar-stack.yml
      variables:
        CodeSha256: ${awslambda.CodeSha256 example-function-02}
        ...
