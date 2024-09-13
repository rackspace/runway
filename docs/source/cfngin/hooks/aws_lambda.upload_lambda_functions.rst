.. _aws_lambda hook:

##################################
aws_lambda.upload_lambda_functions
##################################

.. deprecated:: 2.5.0
  Replaced by :ref:`awslambda.PythonFunction hook`.


:Hook Path: ``runway.cfngin.hooks.aws_lambda.upload_lambda_functions``


Build Lambda payloads from user configuration and upload them to S3 using the following process:

#. Constructs ZIP archives containing files matching specified patterns for each function.
#. Uploads the result to Amazon S3
#. Returns a |Dict| of "*function name*: :class:`troposphere.awslambda.Code`".

The returned value can retrieved using the :ref:`hook_data Lookup <hook_data lookup>` or by interacting with the :class:`~runway.context.CfnginContext` object passed to the |Blueprint|.

Configuration consists of some global options, and a dictionary of function specifications.
In the specifications, each key indicating the name of the function (used for generating names for artifacts), and the value determines what files to include in the ZIP (see more details below).

If a ``requirements.txt`` file or ``Pipfile/Pipfile.lock`` files are found at the root of the provided ``path``, the hook will use the appropriate method to package dependencies with your source code automatically.
If you want to explicitly use ``pipenv`` over ``pip``, provide ``use_pipenv: true`` for the function.

Docker can be used to collect python dependencies instead of using system python to build appropriate binaries for Lambda.
This can be done by including the ``dockerize_pip`` configuration option which can have a value of ``true`` or ``non-linux``.

Payloads are uploaded to either the |cfngin_bucket| or an explicitly specified bucket, with the object key containing it's checksum to allow repeated uploads to be skipped in subsequent runs.

.. versionchanged:: 2.8.0
  Use of pipenv now requires version ``>= 2022.8.13``.
  This is the version that changed how ``requirements.txt`` files are generated.


****
Args
****

.. data:: bucket
  :type: str | None
  :value: None
  :noindex:

  Custom bucket to upload functions to. If not provided, |cfngin_bucket| will be used.

.. data:: bucket_region
  :type: str | None
  :value: None
  :noindex:

  The region in which the bucket should exist.
  If not provided, :attr:`~cfngin.config.cfngin_bucket_region` will be used.

.. data:: prefix
  :type: str | None
  :value: None
  :noindex:

  S3 key prefix to prepend to the uploaded zip name.

.. data:: follow_symlinks
  :type: bool
  :value: False
  :noindex:

  Whether symlinks should be followed and included with the zip artifact.

.. data:: payload_acl
  :type: runway.cfngin.hooks.aws_lambda.PayloadAclTypeDef
  :value: private
  :noindex:

  The canned S3 object ACL to be applied to the uploaded payload.

.. data:: functions
  :type: dict[str, Any]
  :noindex:

  Configurations of desired payloads to build.
  Keys correspond to function names, used to derive key names for the payload.
  Each value should itself be a dictionary, with the following data:

  .. data:: docker_file
    :type: str | None
    :value: None
    :noindex:

    Path to a local DockerFile that will be built and used for ``dockerize_pip``.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: docker_image
    :type: str | None
    :value: None
    :noindex:

    Custom Docker image to use  with ``dockerize_pip``.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: dockerize_pip
    :type: bool | Literal["non-linux"] | None
    :value: None
    :noindex:

    Whether to use Docker when restoring dependencies with pip.
    Can be set to ``true``/``false`` or the special string ``non-linux`` which will only run on non Linux systems.
    To use this option Docker must be installed.

  .. data:: exclude
    :type: list[str] | str
    :value: None
    :noindex:

    Pattern or list of patterns of files to exclude from the payload.
    If provided, any files that match will be ignored, regardless of whether they match an inclusion pattern.

    Commonly ignored files are already excluded by default, such as ``.git``, ``.svn``, ``__pycache__``, ``*.pyc``, ``.gitignore``, etc.

  .. data:: include
    :type: list[str] | str | None
    :value: None
    :noindex:

    Pattern or list of patterns of files to include in the payload.
    If provided, only files that match these patterns will be included in the payload.

    Omitting it is equivalent to accepting all files that are not otherwise excluded.

  .. data:: path
    :type: str
    :noindex:

    Base directory of the Lambda function payload content.
    If it not an absolute path, it will be considered relative to the directory containing the CFNgin configuration file in use.

    Files in this directory will be added to the payload ZIP, according to the include and exclude patterns.
    If no patterns are provided, all files in this directory (respecting default exclusions) will be used.

    Files are stored in the archive with path names relative to this directory.
    So, for example, all the files contained directly under this directory will be added to the root of the ZIP file.

  .. data:: python_path
    :type: str | None
    :value: None
    :noindex:

    Absolute path to a python interpreter to use for ``pip``/``pipenv`` actions.
    If not provided, the current python interpreter will be used for ``pip`` and ``pipenv`` will be used from the current ``$PATH``.

  .. data:: runtime
    :type: str | None
    :value: None
    :noindex:

    Runtime of the AWS Lambda Function being uploaded.
    Used with ``dockerize_pip`` to automatically select the appropriate Docker image to use.
    Must provide exactly one of ``docker_file``, ``docker_image``, or ``runtime``.

  .. data:: use_pipenv
    :type: bool | None
    :value: False
    :noindex:

    Will determine if pipenv will be used to generate requirements.txt from an existing Pipfile.
    To use this option pipenv must be installed.



*******
Example
*******

.. code-block:: yaml
  :caption: Hook Configuration

  pre_deploy:
    - path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
      required: true
      enabled: true
      data_key: lambda
      args:
        bucket: custom-bucket
        follow_symlinks: true
        prefix: cloudformation-custom-resources/
        payload_acl: authenticated-read
        functions:
          MyFunction:
            path: ./lambda_functions
            dockerize_pip: non-linux
            use_pipenv: true
            runtime: python3.9
            include:
              - '*.py'
              - '*.txt'
            exclude:
              - '*.pyc'
              - test/

.. code-block:: python
  :caption: Blueprint Usage

  """Example Blueprint."""
  from __future__ import annotations

  from typing import cast

  from troposphere.awslambda import Code, Function

  from runway.cfngin.blueprints.base import Blueprint


  class LambdaBlueprint(Blueprint):
      """Example Blueprint."""

      def create_template(self) -> None:
          """Create a template from the blueprint."""
          code = cast(Code, self.context.hook_data["lambda"]["MyFunction"])

          self.template.add_resource(
              Function(
                  "MyFunction",
                  Code=code,
                  Handler="my_function.handler",
                  Role="...",
                  Runtime="python3.9",
              )
          )
