.. _hook definition: configuration.html#pre-post-hooks
.. _package_sources: configuration.html#remote-package
.. _`Pre & Post Hooks`: configuration.html#pre-post-hooks
.. _staticsite: ../module_configuration/staticsite.html
.. _sys_path: configuration.html#module-paths

#####
Hooks
#####

A hook is a python function or class method that is executed before or after the action is taken.
To see how to define hooks in a config file see the `Pre & Post Hooks`_ documentation.


**************
Built-in Hooks
**************

acm.Certificate
===============

.. rubric:: Requirements

- Route 53 hosted zone

    - authoritative for the domain the certificate is being created for
    - in the same AWS account as the certificate being created


.. rubric:: Description

Manage a DNS validated certificate in AWS Certificate Manager.

When used in the **pre_build** or **post_build** stage this hook will create a CloudFormation stack containing a DNS validated certificate.
It will automatically create a record in Route 53 to validate the certificate and wait for the stack to complete before returning the ``CertificateArn`` as hook data.
The CloudFormation stack also outputs the ARN of the certificate as ``CertificateArn`` so that it can be referenced from other stacks.

When used in the **pre_destroy** or **post_destroy** stage this hook will delete the validation record from Route 53 then destroy the stack created during a deploy stage.

If the hook fails during a deploy stage (e.g. stack rolls back or Route 53 can't be updated) all resources managed by this hook will be destroyed.
This is done to avoid orphaning resources/record sets which would cause errors during subsequent runs.
Resources effected include the CloudFormation stack it creates, ACM certificate, and Route 53 validation record.

.. rubric:: Hook Path

``runway.cfngin.hooks.acm.Certificate``


.. rubric:: Args

**alt_names (Optional[List[str]])**
    Additional FQDNs to be included in the Subject Alternative Name extension of the ACM certificate.
    For example, you can add *www.example.net* to a certificate for which the ``domain`` field is
    *www.example.com* if users can reach your site by using either name.

**domain (str)**
    The fully qualified domain name (FQDN), such as *www.example.com*, with which you want to secure an ACM certificate.
    Use an asterisk (``*``) to create a wildcard certificate that protects several sites in the same domain.
    For example, *\*.example.com* protects *www.example.com*, *site.example.com*, and *images.example.com*.

**hosted_zone_id (str)**
    The ID of the Route 53 Hosted Zone that contains the resource record sets that you want to change.
    This must exist in the same account that the certificate will be created in.

**stack_name (Optional[str])**
    Provide a name for the stack used to create the certificate. If not provided, the domain is used (replacing ``.`` with ``-``).
    If the is provided in a deploy stage, its needs to be provided in the matching destroy stage.

**ttl (Optional[int])**
    The resource record cache time to live (TTL), in seconds. (*default:* ``300``)


.. rubric:: Example
.. code-block:: yaml

    namespace: example
    cfngin_bucket: ''

    sys_path: ./

    pre_build:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}

    stack:
      sampleapp:
        class_path: blueprints.sampleapp.BlueprintClass
        variables:
          cert_arn: ${rxref www-example-com::CertificateArn}

    post_destroy:
      acm-cert:
        path: runway.cfngin.hooks.acm.Certificate
        required: true
        args:
          domain: www.example.com
          hosted_zone_id: ${rxref example-com::HostedZone}


aws_lambda.upload_lambda_functions
==================================

.. rubric:: Description

Build Lambda payloads from user configuration and upload them to S3.

Constructs ZIP archives containing files matching specified patterns for
each function, uploads the result to Amazon S3, then stores objects (of
type :class:`troposphere.awslambda.Code`) in the context's hook data,
ready to be referenced in blueprints.

Configuration consists of some global options, and a dictionary of function
specifications. In the specifications, each key indicating the name of the
function (used for generating names for artifacts), and the value
determines what files to include in the ZIP (see more details below).

If a ``requirements.txt`` or ``Pipfile/Pipfile.lock`` files are found at the root of the provided ``path``, the hook will use the appropriate method to package dependencies with your source code automatically. If you want to explicitly use ``pipenv`` over ``pip``, provide ``use_pipenv: true`` for the function.

Docker can be used to collect python dependencies instead of using system python to build appropriate binaries for Lambda.
This can be done by including the ``dockerize_pip`` configuration option which can have a value of ``true`` or ``non-linux``.

Payloads are uploaded to either a custom bucket or the CFNgin default
bucket, with the key containing it's checksum, to allow repeated uploads
to be skipped in subsequent runs.


.. rubric:: Hook Path

``runway.cfngin.hooks.aws_lambda.upload_lambda_functions``


.. rubric:: Args

**bucket (Optional[str])**
    Custom bucket to upload functions to. Omitting it will cause the default CFNgin bucket to be used.

**bucket_region (Optional[str])**
    The region in which the bucket should exist.
    If not given, the region will be either be that of the global ``cfngin_bucket_region`` setting, or else the region in use by the provider.

**prefix (Optional[str])**
    S3 key prefix to prepend to the uploaded zip name.

**follow_symlinks (Optional[bool])**
    Will determine if symlinks should be followed and included with the zip artifact. (*default:* ``False``)

**payload_acl (Optional[str])**
    The canned S3 object ACL to be applied to the uploaded payload. (*default: private*)

**functions (Dict[str, Any])**
    Configurations of desired payloads to build.
    Keys correspond to function names, used to derive key names for the payload.
    Each value should itself be a dictionary, with the following data:

    **docker_file (Optional[str])**
        Path to a local DockerFile that will be built and used for
        ``dockerize_pip``. Must provide exactly one of ``docker_file``,
        ``docker_image``, or ``runtime``.

    **docker_image (Optional[str])**
        Custom Docker image to use  with ``dockerize_pip``. Must
        provide exactly one of ``docker_file``, ``docker_image``, or
        ``runtime``.

    **dockerize_pip (Optional[Union[str, bool]])**
        Whether to use Docker when restoring dependencies with pip.
        Can be set to ``true``/``false`` or the special string ``non-linux``
        which will only run on non Linux systems.
        To use this option Docker must be installed.

    **exclude (Optional[Union[str, List[str]]])**
        Pattern or list of patterns of files to exclude from the
        payload. If provided, any files that match will be ignored,
        regardless of whether they match an inclusion pattern.

        Commonly ignored files are already excluded by default,
        such as ``.git``, ``.svn``, ``__pycache__``, ``*.pyc``,
        ``.gitignore``, etc.

    **include (Optional[Union[str, List[str]]])**
        Pattern or list of patterns of files to include in the
        payload. If provided, only files that match these
        patterns will be included in the payload.

        Omitting it is equivalent to accepting all files that are
        not otherwise excluded.

    **path (str)**
        Base directory of the Lambda function payload content.
        If it not an absolute path, it will be considered relative
        to the directory containing the CFNgin configuration file
        in use.

        Files in this directory will be added to the payload ZIP,
        according to the include and exclude patterns. If not
        patterns are provided, all files in this directory
        (respecting default exclusions) will be used.

        Files are stored in the archive with path names relative to
        this directory. So, for example, all the files contained
        directly under this directory will be added to the root of
        the ZIP file.

    **python_path (Optional[str])**
        Absolute path to a python interpreter to use for ``pip``/``pipenv``
        actions. If not provided, the current python interpreter will be used
        for ``pip`` and ``pipenv`` will be used from the current ``$PATH``.

    **runtime (Optional[str])**
        Runtime of the AWS Lambda Function being uploaded. Used with
        ``dockerize_pip`` to automatically select the appropriate
        Docker image to use. Must provide exactly one of
        ``docker_file``, ``docker_image``, or ``runtime``.

    **use_pipenv (Optional[bool])**:
        Will determine if pipenv will be used to generate requirements.txt
        from an existing Pipfile. To use this option pipenv must be installed.


.. rubric:: Example

**Hook configuration**

.. code-block:: yaml

    pre_build:
      upload_functions:
        path: runway.cfngin.hooks.aws_lambda.upload_lambda_functions
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
              runtime: python3.8
              include:
                - '*.py'
                - '*.txt'
              exclude:
                - '*.pyc'
                - test/

**Blueprint Usage**

.. code-block:: python

    from troposphere.awslambda import Function
    from runway.cfngin.blueprints.base import Blueprint

    class LambdaBlueprint(Blueprint):
        def create_template(self):
            code = self.context.hook_data['lambda']['MyFunction']

            self.template.add_resource(
                Function(
                    'MyFunction',
                    Code=code,
                    Handler='my_function.handler',
                    Role='...',
                    Runtime='python2.7'
                )
            )


build_staticsite.build
======================

.. rubric:: Description

Build static site. Used by the staticsite_ module type.


.. rubric:: Hook Path

``runway.hooks.staticsite.build_staticsite.build``


.. rubric:: Args

See staticsite_ module documentation for details.


cleanup_s3.purge_bucket
=======================

.. rubric:: Description

Delete objects in bucket. Primarily used as a ``pre_destroy`` hook before deleting an S3 bucket.


.. rubric:: Hook Path

``runway.hooks.cleanup_s3.purge_bucket``


.. rubric:: Args

**bucket_name (str)**
    Name of the S3 bucket.

**bucket_output_lookup (str)**
    Value to pass to :class:`runway.cfngin.lookups.handlers.output.OutputLookup` to retrieve an S3 bucket name.

**bucket_rxref_lookup (str)**
    Value to pass to :class:`runway.cfngin.lookups.handlers.rxref.RxrefLookup` to retrieve an S3 bucket name.

**bucket_xref_lookup (str)**
    Value to pass to :class:`runway.cfngin.lookups.handlers.xref.XrefLookup` to retrieve an S3 bucket name.


cleanup_ssm.delete_param
========================

.. rubric:: Description

Delete SSM parameter. Primarily used when an SSM parameter is created by a hook rather than CloudFormation.


.. rubric:: Hook Path

``runway.hooks.cleanup_ssm.delete_param``


.. rubric:: Args

**parameter_name (str)**
    Name of an SSM parameter.


command.run_command
===================

.. rubric:: Description

Run a custom command as a hook.


.. rubric:: Hook Path

``runway.cfngin.hooks.command.run_command``


.. rubric:: Args

**command (Union[str, List[str]])**
    Command(s) to run.

**capture (bool)**
    If enabled, capture the command's stdout and stderr,
    and return them in the hook result. (*default:* ``False``)

**interactive (bool)**
    If enabled, allow the command to interact with
    stdin. Otherwise, stdin will be set to the null device.
    (*default:* ``False``)

**ignore_status (bool)**
    Don't fail the hook if the command returns a
    non-zero status. (*default:* ``False``)

**quiet (bool)**
    Redirect the command's stdout and stderr to the null
    device, silencing all output. Should not be enabled if
    ``capture`` is also enabled. (*default:* ``False``)

**stdin (Optional[str])**
    String to send to the stdin of the command.
    Implicitly disables ``interactive``.
**env (Optional[Dict[str, str]])**
    Dictionary of environment variable
    overrides for the command context. Will be merged with the current
    environment.
**\**\kwargs (Any)**
    Any other arguments will be forwarded to the
    ``subprocess.Popen`` function. Interesting ones include: ``cwd``
    and ``shell``.


.. rubric:: Example

.. code-block:: yaml

    pre_build:
      command_copy_environment:
        path: runway.cfngin.hooks.command.run_command
        required: true
        enabled: true
        data_key: copy_env
        args:
          command: ['cp', 'environment.template', 'environment']
      command_git_rev_parse:
        path: runway.cfngin.hooks.command.run_command
        required: true
        enabled: true
        data_key: get_git_commit
        args:
          command: ['git', 'rev-parse', 'HEAD']
          cwd: ./my-git-repo
          capture: true
      command_npm_install:
        path: runway.cfngin.hooks.command.run_command
        args:
          command: '`cd $PROJECT_DIR/project; npm install`'
          env:
            PROJECT_DIR: ./my-project
            shell: true


ecs.create_clusters
===================

.. rubric:: Description

Create ECS clusters.


.. rubric:: Hook Path

``runway.cfngin.hooks.ecs.create_clusters``


.. rubric:: Args

**clusters (List[str])**
    Names of clusters to create.


iam.create_ecs_service_role
===========================

.. rubric:: Description

Create ecsServiceRole, which has to be named exactly that currently.

http://docs.aws.amazon.com/AmazonECS/latest/developerguide/IAM_policies.html#service_IAM_role


.. rubric:: Hook Path

``runway.cfngin.hooks.iam.create_ecs_service_role``


.. rubric:: Args

**role_name (str)**
    Name of the role to create. (*default: ecsServiceRole*)


iam.ensure_server_cert_exists
=============================

.. rubric:: Description

Ensure server cert exists.


.. rubric:: Hook Path

``runway.cfngin.hooks.iam.ensure_server_cert_exists``


.. rubric:: Args

**cert_name (str)**
    Name of the certificate that should exist.

**prompt (bool)**
    Whether to prompt to upload a certificate if one does not exist. (*default:* ``True``)


keypair.ensure_keypair_exists
=============================

.. rubric:: Description

Ensure a specific keypair exists within AWS. If the key doesn't exist, upload it.


.. rubric:: Hook Path

``runway.cfngin.hooks.keypair.ensure_keypair_exists``


.. rubric:: Args

**keypair (str)**
    Name of the key pair to create

**ssm_parameter_name (Optional[str])**
    Path to an SSM store parameter
    to receive the generated private key, instead of importing it or
    storing it locally.

**ssm_key_id (Optional[str])**
    ID of a KMS key to encrypt the SSM
    parameter with. If omitted, the default key will be used.

**public_key_path (Optional[str])**
    Path to a public key file to be
    imported instead of generating a new key. Incompatible with the
    SSM options, as the private key will not be available for
    storing.


route53.create_domain
=====================

.. rubric:: Description

Create a domain within route53.


.. rubric:: Hook Path

``runway.cfngin.hooks.route53.create_domain``


.. rubric:: Args

**domain (str)**
    Domain name for the Route 53 hosted zone to be created.


upload_staticsite.get_distribution_data
=======================================

.. rubric:: Description

Retrieve information about the CloudFront distribution.
Used by the staticsite_ module type.


.. rubric:: Hook Path

``runway.hooks.staticsite.upload_staticsite.get_distribution_data``


.. rubric:: Args

See staticsite_ module documentation for details.


upload_staticsite.sync
======================

.. rubric:: Description

Sync static website to S3 bucket. Used by the staticsite_ module type.


.. rubric:: Hook Path

``runway.hooks.staticsite.upload_staticsite.sync``


.. rubric:: Args

See staticsite_ module documentation for details.


*********************
Writing A Custom Hook
*********************

A custom hook must be in an executable, importable python package or standalone file.
The hook must be importable using your current ``sys.path``.
This takes into account the sys_path_ defined in the config file as well as any ``paths`` of package_sources_.

The hook must accept a minimum of two arguments, ``context`` and ``provider``.
Aside from the required arguments, it can have any number of additional arguments or use ``**kwargs`` to accept anything passed to it.
The values for these additional arguments come from the ``args`` key of the `hook definition`_.

The hook must return ``True`` or a truthy object if it was successful.
It must return ``False`` or a falsy object if it failed.
This signifies to CFNgin whether or not to halt execution if the hook is ``required``.
If data is returned, it can be accessed by subsequent hooks, lookups, or Blueprints from the context object.
It will be stored as ``context.hook_data[data_key]`` where ``data_key`` is the value set in the `hook definition`_.

If using boto3 in a hook, use ``context.get_session()`` instead of creating a new session to ensure the correct credentials are used.

.. code-block::

    """context.get_session() example."""
    from runway.cfngin.context import Context
    from runway.cfngin.providers.aws.default import Provider

    def do_something(context: Context, provider: Provider, **kwargs: str) -> None:
        """Do something."""
        session = context.get_session()
        s3_client = session.client('s3')


Example Hook Function
=====================

.. rubric:: local_path/hooks/my_hook.py
.. code-block:: python

    """My hook."""
    from typing import Dict

    from runway.cfngin.context import Context
    from runway.cfngin.providers.aws.default import Provider


    def do_something(context: Context,
                     provider: Provider,
                     is_failure: bool = True,
                     **kwargs: str
                     ) -> Dict[str, str]:
        """Do something."""
        if is_failure:
            return None
        return {'result': f"You are not a failure {kwargs.get('name', 'Kevin')}."}

.. rubric:: local_path/cfngin.yaml
.. code-block:: yaml

    namespace: example
    sys_path: ./

    pre_build:
      my_hook_do_something:
        path: hooks.my_hook.do_something
        args:
          is_failure: False


Example Hook Class
==================

.. rubric:: local_path/hooks/my_hook.py
.. code-block:: python

    """My hook."""
    import logging
    from typing import Dict

    from runway.cfngin.hooks.base import Hook

    LOGGER = logging.getLogger(__name__)

    class MyClass(Hook):
        """My class does a thing.

        Keyword Args:
            is_failure (bool): Force the hook to fail if true.
            name (str): Name used in the response.

        Returns:
            Dict[str, str]: Response message is stored in ``result``.

        Example:
        .. code-block:: yaml

          pre_build:
            my_hook_do_something:
              path: hooks.my_hook.MyClass
              args:
                is_failure: False
                name: Karen

        """

        def post_deploy(self) -> Dict[str, str]:
            """Run during the **post_deploy** stage."""
            if self.args.is_failure:
                return None
            return {'result': f"You are not a failure {self.args.name}."

        def post_destroy(self) -> None:
            """Run during the **post_destroy** stage."""
            LOGGER.error('post_destroy is not supported by this hook')

        def pre_deploy(self) -> None:
            """Run during the **pre_deploy** stage."""
            LOGGER.error('pre_deploy is not supported by this hook')

        def pre_destroy(self) -> None:
            """Run during the **pre_destroy** stage."""
            LOGGER.error('pre_destroy is not supported by this hook')

.. rubric:: local_path/cfngin.yaml
.. code-block:: yaml

    namespace: example
    sys_path: ./

    pre_build:
      my_hook_do_something:
        path: hooks.my_hook.MyClass
        args:
          is_failure: False
          name: Karen

