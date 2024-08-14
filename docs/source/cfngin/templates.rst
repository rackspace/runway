#########
Templates
#########

CloudFormation templates can be provided via :term:`Blueprints <Blueprint>` or JSON/YAML.
JSON/YAML templates are specified for :class:`stacks <cfngin.stack>` via the :attr:`~cfngin.stack.template_path` config.



*****************
Jinja2 Templating
*****************

Templates with a ``.j2`` extension will be parsed using :link:`Jinja2 <jinja>`.
The CFNgin ``context`` and ``mappings`` objects and stack ``variables`` objects are available for use in the template:

.. code-block:: yaml

    Description: TestTemplate
    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Properties:
          BucketName: {{ context.environment.foo }}-{{ variables.myparamname }}
