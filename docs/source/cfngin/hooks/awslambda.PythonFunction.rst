.. _awslambda.PythonFunction hook:

########################
awslambda.PythonFunction
########################

:Hook Path: :class:`runway.cfngin.hooks.awslambda.PythonFunction`


This hook creates deployment packages for Python Lambda Functions, uploads them to S3, and returns data about the deployment package.

The return value can be retrieved using the :ref:`hook_data lookup` or by interacting with the :class:`~runway.context.CfnginContext` object passed to the |Blueprint|.

To use this hook to install dependencies, it must be able to find project metadata files.
This can include ``pyproject.toml`` & ``poetry.lock`` files (poetry) or a ``requirements.txt`` file (pip).
The project metadata files can exist either in the source code directory (value of ``source_code`` arg) or in the same directory as the CFNgin configuration file.
If metadata files are not found, dependencies will not be included in the deployment package.

This hook will always use Docker to install/compile dependencies unless explicitly configured not to.
It is recommended to always use Docker to ensure a clean and consistent build.
It also ensures that binary files built during the install process are compatible with AWS Lambda.


.. versionadded:: 2.5.0

.. versionchanged:: 2.8.0
  Use of pipenv now requires version ``>= 2022.8.13``.
  This is the version that changed how ``requirements.txt`` files are generated.

.. versionchanged:: 3.0.0
  Removed support for pipenv.



****
Args
****

Arguments that can be passed to the hook in the :attr:`~cfngin.hook.args` field.


.. note::
  Documentation for each field is automatically generated from class attributes in the source code.
  When specifying the field, exclude the class name.


.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.bucket_name
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.cache_dir
  :noindex:

  If not provided, the cache directory is ``.runway/awslambda/pip_cache`` within the current working directory.

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.docker
  :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.disabled
    :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.extra_files
    :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.file
    :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.image
    :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.name
    :noindex:

  .. autoattribute:: runway.cfngin.hooks.awslambda.models.args.DockerOptions.pull
    :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.extend_gitignore
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.extend_pip_args
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.object_prefix
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.runtime
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.slim
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.source_code
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.strip
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.use_cache
  :noindex:

.. autoattribute:: runway.cfngin.hooks.awslambda.models.args.PythonHookArgs.use_poetry
  :noindex:



************
Return Value
************

.. autoclass:: runway.cfngin.hooks.awslambda.models.responses.AwsLambdaHookDeployResponse
  :exclude-members: Config
  :member-order: alphabetical
  :no-inherited-members:
  :no-show-inheritance:
  :no-special-members:
  :noindex:



*******
Example
*******

.. code-block:: docker
  :caption: Dockerfile

  FROM public.ecr.aws/sam/build-python3.9:latest

  RUN yum install libxml2-devel xmlsec1-devel xmlsec1-openssl-devel libtool-ltdl-devel -y

.. code-block:: yaml
  :caption: cfngin.yml

  namespace: ${namespace}
  cfngin_bucket: ${cfngin_bucket}
  src_path: ./

  pre_deploy:
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      data_key: awslambda.example-function-no-docker
      args:
        bucket_name: ${bucket_name}
        docker:
          disabled: true
        extend_gitignore:
          - "*.lock"
          - '*.md'
          - '*.toml'
          - tests/
        extend_pip_args:
          - '--proxy'
          - '[user:passwd@]proxy.server:port'
        runtime: python3.9
        slim: false
        source_code: ./src/example-function
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      data_key: awslambda.example-function
      args:
        bucket_name: ${bucket_name}
        # docker:  # example of default & inferred values
        #   disabled: false  # default value
        #   image: public.ecr.aws/sam/build-python3.9:latest  # inferred from runtime
        #   pull: true  # default value
        extend_gitignore:
          - "*.lock"
          - '*.md'
          - '*.toml'
          - tests/
        extend_pip_args:
          - '--proxy'
          - '[user:passwd@]proxy.server:port'
        runtime: python3.9
        source_code: ./src/example-function
    - path: runway.cfngin.hooks.awslambda.PythonFunction
      data_key: awslambda.xmlsec
      args:
        bucket_name: ${bucket_name}
        docker:
          extra_files:
            - /usr/lib64/libltdl.so.*
            - /usr/lib64/libxml2.so.*
            - /usr/lib64/libxmlsec1-openssl.so
            - /usr/lib64/libxmlsec1.so.*
            - /usr/lib64/libxslt.so.*
          file: ./Dockerfile
          pull: false
        extend_gitignore:
          - "*.lock"
          - '*.md'
          - '*.toml'
          - tests/
        source_code: ./src/xmlsec-function
        strip: false

  stacks:
    - name: example-stack
      class_path: blueprints.ExampleBlueprint
      parameters:
        XmlCodeSha256: ${awslambda.CodeSha256 awslambda.xmlsec}
        XmlRuntime: ${awslambda.Runtime awslambda.xmlsec}
        XmlS3Bucket: ${awslambda.S3Bucket awslambda.xmlsec}
        XmlS3Key: ${awslambda.S3Key awslambda.xmlsec}
    ...
