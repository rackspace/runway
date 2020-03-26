.. _Blueprints: ../terminology.html#blueprint

==========
Templates
==========

CloudFormation templates can be provided via Blueprints_ or JSON/YAML.
JSON/YAML templates are specified for stacks via the ``template_path`` config
option (see `Stacks <configuration.html#stacks>`_).


Jinja2 Templating
=================

Templates with a ``.j2`` extension will be parsed using `Jinja2
<http://jinja.pocoo.org/>`_. The CFNgin ``context`` and ``mappings`` objects
and stack ``variables`` objects are available for use in the template:

.. code-block:: yaml

    Description: TestTemplate
    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Properties:
          BucketName: {{ context.environment.foo }}-{{ variables.myparamname }}
