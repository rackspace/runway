.. _cfngin-lookups:

#######
Lookups
#######

.. important::
  Runway lookups and CFNgin lookups are not interchangeable.
  While they  do share a similar base class and syntax, they exist in two different registries.
  Runway config files can't use CFNgin lookups just as the CFNgin config cannot use Runway lookups.

Runway's CFNgin provides the ability to dynamically replace values in the config via a concept called lookups.
A lookup is meant to take a value and convert it by calling out to another service or system.

A lookup is denoted in the config with the ``${<lookup type> <lookup input>}`` syntax.

Lookups are only resolved within :ref:`Variables <cfngin-variables>`.
They can be nested in any part of a YAML data structure and within another lookup itself.

.. note::
  If a lookup has a non-string return value, it can be the only lookup within a field.

  e.g. if ``custom`` returns a list, this would raise an exception::

    Variable: ${custom something}, ${output otherStack::Output}

  This is valid::

    Variable: ${custom something}


For example, given the following:

.. code-block:: yaml

  stacks:
    - name: sg
      class_path: some.stack.blueprint.Blueprint
      variables:
        Roles:
          - ${output otherStack::IAMRole}
        Values:
          Env:
            Custom: ${custom ${output otherStack::Output}}
            DBUrl: postgres://${output dbStack::User}@${output dbStack::HostName}

The |Blueprint| would have access to the following resolved variables dictionary:

.. code-block:: python

  {
      "Roles": ["other-stack-iam-role"],
      "Values": {
          "Env": {
              "Custom": "custom-output",
              "DBUrl": "postgres://user@hostname",
          },
      },
  }

.. contents::
  :depth: 4


----


***
cfn
***

.. important::
  The Stack must exist in CloudFormation before the config using this Lookup begins processing to successfully get a value.
  This means that it must have been deployed using another Runway module, deployed from a config that is run before the one using it, deployed manually, or deployed in the same config using :attr:`~cfngin.stack.required`/:attr:`~cfngin.stack.required_by` to specify a dependency between the Stacks.

Retrieve a value from CloudFormation Stack Outputs.

The query syntax for this lookup is ``<stack-name>.<output-name>``.
When specifying the output name, be sure to use the *Logical ID* of the output; not the *Export.Name*.

If the Lookup is unable to find a CloudFormation Stack Output matching the provided query, the default value is returned or an exception is raised to show why the value could be be resolved (e.g. Stack does not exist or output does not exist on the Stack).

.. seealso::
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.

.. rubric:: Example
.. code-block:: yaml

  namespace: example

  stacks:
    - ...
      variables:
        VpcId: ${cfn ${namespace}-vpc.Id}

Given the above config file, the lookup will get the value of the Output named **Id** from Stack **example-vpc**.


----


***
ecr
***

Retrieve a value from AWS Elastic Container Registry (ECR).

This Lookup only supports very specific queries.

Supported Queries
=================

login-password
--------------

Get a password to login to ECR registry.

The returned value can be passed to the login command of the container client of your preference, such as the :ref:`Docker CFNgin hook <cfngin.hooks.docker>`.
After you have authenticated to an Amazon ECR registry with this Lookup, you can use the client to push and pull images from that registry as long as your IAM principal has access to do so until the token expires.
The authorization token is valid for **12 hours**.

.. rubric:: Arguments

This Lookup does not support any arguments.

.. rubric:: Example
.. code-block:: yaml

  pre_deploy:
    - path: runway.cfngin.hooks.docker.login
      args:
        password: ${ecr login-password}
        ...


----

.. _`output lookup`:

******
output
******

The output_ lookup takes a value of the format: ``<stack name>::<output name>`` and retrieves the Output from the given Stack name within the current |namespace|.

CFNgin treats output lookups differently than other lookups by auto adding the referenced stack in the lookup as a requirement to the stack whose variable the output value is being passed to.

You can specify an output lookup with the following syntax:

.. code-block:: yaml

  ConfVariable: ${output someStack::SomeOutput}


----

.. _`default lookup`:

*******
default
*******

The default_ lookup type will check if a value exists for the variable in the environment file, then fall back to a default defined in the CFNgin config if the environment file doesn't contain the variable.
This allows defaults to be set at the config file level, while granting the user the ability to override that value per environment.

Format of value:

.. code-block:: yaml

  <env_var>::<default value>

.. rubric:: Example
.. code-block:: yaml

  Groups: ${default app_security_groups::sg-12345,sg-67890}

If ``app_security_groups`` is defined in the environment file, its defined value will be returned. Otherwise, ``sg-12345,sg-67890`` will be the returned value.

.. note::
  The default_ lookup only supports checking if a variable is defined in an environment file.
  It does not support other embedded lookups to see if they exist.
  Only checking variables in the environment file are supported.
  If you attempt to have the default lookup perform any other lookup that fails, CFNgin will throw an exception for that lookup and will exit before it gets a chance to fall back to the default in your config.


----


.. _`kms lookup`:

***
kms
***

The kms_ lookup type decrypts its input value.

As an example, if you have a database and it has a parameter called ``DBPassword`` that you don't want to store in clear text in your config (maybe because you want to check it into your version control system to share with the team), you could instead encrypt the value using ``kms``.

.. rubric:: Example
.. code-block:: shell

  # We use the aws cli to get the encrypted value for the string
  # "PASSWORD" using the master key called 'myKey' in us-east-1
  $ aws --region us-east-1 kms encrypt --key-id alias/myKey \
      --plaintext "PASSWORD" --output text --query CiphertextBlob

  CiD6bC8t2Y<...encrypted blob...>

  # With CFNgin we would reference the encrypted value like:
  DBPassword: ${kms us-east-1@CiD6bC8t2Y<...encrypted blob...>}

  # The above would resolve to
  DBPassword: PASSWORD

This requires that the person using CFNgin has access to the master key used to encrypt the value.

It is also possible to store the encrypted blob in a file (useful if the value is large) using the ``file://`` prefix, ie:

.. code-block:: yaml

  DockerConfig: ${kms file://dockercfg}

.. note::
  Lookups resolve the path specified with ``file://`` relative to the location of the config file, not where the CFNgin command is run.


----


.. _`xref lookup`:

****
xref
****

.. deprecated:: 1.11.0
  Replaced by cfn_

The xref_ lookup type is very similar to the output_ lookup type, the difference being that xref_ resolves output values from stacks that aren't contained within the current CFNgin |namespace|, but are existing Stacks containing outputs within the same region on the AWS account you are deploying into.
xref_ allows you to lookup these outputs from the Stacks already in your account by specifying the stacks fully qualified name in the CloudFormation console.

Where the output_ type will take a Stack name and use the current context to expand the fully qualified stack name based on the |namespace|, xref_ skips this expansion because it assumes you've provided it with the fully qualified stack name already.
This allows you to reference output values from any CloudFormation Stack in the same region.

Also, unlike the output_ lookup type, xref_ doesn't impact stack requirements.

.. rubric:: Example
.. code-block:: yaml

  ConfVariable: ${xref fully-qualified-stack::SomeOutput}


----


.. _`rxref lookup`:

*****
rxref
*****

The rxref_ lookup type is very similar to the xref_ lookup type.
Where the xref_ type assumes you provided a fully qualified stack name, rxref_, like output_ expands and retrieves the output from the given Stack name within the current |namespace|, even if not defined in the CFNgin config you provided it.

Because there is no requirement to keep all stacks defined within the same CFNgin YAML config, you might need the ability to read outputs from other Stacks deployed by CFNgin into your same account under the same |namespace|.
rxref_ gives you that ability.
This is useful if you want to break up very large configs into smaller groupings.

Also, unlike the output_ lookup type, rxref_ doesn't impact Stack requirements.

.. rubric:: Example
.. code-block:: yaml

  # in example-us-east-1.env
  namespace: MyNamespace

  # in cfngin.yaml
  ConfVariable: ${rxref my-stack::SomeOutput}

  # the above would effectively resolve to
  ConfVariable: ${xref MyNamespace-my-stack::SomeOutput}

Although possible, it is not recommended to use ``rxref`` for stacks defined within the same CFNgin YAML config.


----


.. _`file lookup`:

****
file
****

The file_ lookup type allows the loading of arbitrary data from files on disk.
The lookup additionally supports using a ``codec`` to manipulate or wrap the file contents prior to injecting it.
The parameterized-b64 ``codec`` is particularly useful to allow the interpolation of CloudFormation parameters in a UserData attribute of an instance or launch configuration.

Basic examples:

.. code-block:: shell

  # We've written a file to /some/path:
  $ echo "hello there" > /some/path

  # In CFNgin we would reference the contents of this file with the following
  conf_key: ${file plain:file://some/path}

  # The above would resolve to
  conf_key: hello there

  # Or, if we used wanted a base64 encoded copy of the file data
  conf_key: ${file base64:file://some/path}

  # The above would resolve to
  conf_key: aGVsbG8gdGhlcmUK

.. rubric:: Supported Codecs

- **plain** - Load the contents of the file untouched. This is the only codec that should be used
  with raw Cloudformation templates (the other codecs are intended for blueprints).
- **base64** - Encode the plain text file at the given path with base64 prior
  to returning it
- **parameterized** - The same as plain, but additionally supports
  referencing CloudFormation parameters to create userdata that's
  supplemented with information from the template, as is commonly needed
  in EC2 UserData. For example, given a template parameter of BucketName,
  the file could contain the following text:

  .. code-block:: shell

    #!/bin/sh
    aws s3 sync s3://{{BucketName}}/somepath /somepath

  and then you could use something like this in the YAML config file:

  .. code-block:: yaml

    UserData: ${file parameterized:/path/to/file}

  resulting in the UserData parameter being defined as:

  .. code-block:: json

    {
        "Fn::Join" : [
            "",
            [
                "#!/bin/sh\naws s3 sync s3://",
                {
                    "Ref" : "BucketName"
                },
                "/somepath /somepath"
            ]
        ]
    }

- **parameterized-b64** - The same as parameterized, with the results additionally
  wrapped in ``{ "Fn::Base64": ... }`` , which is what you actually need for
  EC2 UserData.

  When using parameterized-b64 for UserData, you should use a local parameter defined as such.

  .. code-block:: python

    from troposphere import AWSHelperFn

    "UserData": {
        "type": AWSHelperFn,
        "description": "Instance user data",
        "default": Ref("AWS::NoValue")
    }

  and then assign UserData in a LaunchConfiguration or Instance to ``self.get_variables()["UserData"]``.
  Note that we use AWSHelperFn as the type because the parameterized-b64 codec returns either a Base64 or a GenericHelperFn troposphere object.

- **json** - Decode the file as JSON and return the resulting object.
- **json-parameterized** - Same as ``json``, but applying templating rules from ``parameterized`` to every object *value*.
  Note that object *keys* are not modified.

  Example (an external PolicyDocument):

  .. code-block:: json

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "some:Action"
                ],
                "Resource": "{{MyResource}}"
            }
        ]
    }

- **yaml** - Decode the file as YAML and return the resulting object.
- **yaml-parameterized** - Same as ``json-parameterized``, but using YAML.

  .. code-block:: yaml

    Version: 2012-10-17
    Statement:
      - Effect: Allow
        Action:
          - "some:Action"
        Resource: "{{MyResource}}"


----


***
ssm
***

Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query, the default value is returned or ``ParameterNotFound`` is raised if a default value is not provided.

Parameters of type ``SecureString`` are automatically decrypted.

Parameters of type ``StringList`` are returned as a list.

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.

.. rubric:: Example
.. code-block:: yaml

  stacks:
    - ...
      variables:
        Example: ${ssm /example/secret}


----


.. _`dynamodb lookup`:

********
dynamodb
********

The dynamodb_ lookup type retrieves a value from a DynamoDb table.

As an example, if you have a Dynamo Table named ``TestTable`` and it has an Item with a Primary Partition key called ``TestKey`` and a value named ``BucketName``, you can look it up by using CFNgin.
The lookup key in this case is TestVal

.. rubric:: Example
.. code-block:: yaml

  # We can reference that dynamo value
  BucketName: ${dynamodb us-east-1:TestTable@TestKey:TestVal.BucketName}

  # Which would resolve to:
  BucketName: test-bucket

You can lookup other data types by putting the data type in the lookup.
Valid values are ``S`` (String), ``N`` (Number), ``M`` (Map), ``L`` (List).

.. code-block:: yaml

  ServerCount: ${dynamodb us-east-1:TestTable@TestKey:TestVal.ServerCount[N]}

This would return an int value, rather than a string

You can lookup values inside of a map.

.. code-block:: yaml

  ServerCount: ${dynamodb us-east-1:TestTable@TestKey:TestVal.ServerInfo[M].ServerCount[N]}


----


.. _`envvar lookup`:

******
envvar
******

The envvar_ lookup type retrieves a value from a variable in the shell's environment.

.. rubric:: Example
.. code-block:: shell

  # Set an environment variable in the current shell.
  $ export DATABASE_USER=root

  # In the CFNgin config we could reference the value:
  DBUser: ${envvar DATABASE_USER}

  # Which would resolve to:
  DBUser: root

You can also get the variable name from a file, by using the ``file://`` prefix in the lookup, like so:

.. code-block:: yaml

  DBUser: ${envvar file://dbuser_file.txt}


----


.. _`ami lookup`:

***
ami
***

The ami_ lookup is meant to search for the most recent AMI created that matches the given filters.

Valid arguments::

  region OPTIONAL ONCE:
      e.g. us-east-1@

  owners (comma delimited) REQUIRED ONCE:
      aws_account_id | amazon | self

  name_regex (a regex) REQUIRED ONCE:
      e.g. my-ubuntu-server-[0-9]+

  executable_users (comma delimited) OPTIONAL ONCE:
      aws_account_id | amazon | self

Any other arguments specified are sent as filters to the AWS API.
For example, "architecture:x86_64" will add a filter.

.. code-block:: yaml

  # Grabs the most recently created AMI that is owned by either this account,
  # amazon, or the account id 888888888888 that has a name that matches
  # the regex "server[0-9]+" and has "i386" as its architecture.

  # Note: The region is optional, and defaults to the current CFNgin region
  ImageId: ${ami [<region>@]owners:self,888888888888,amazon name_regex:server[0-9]+ architecture:i386}


----


.. _`hook_data lookup`:

*********
hook_data
*********

When using hooks, you can have the hook store results in the :attr:`CfnginContext.hook_data <runway.context.CfnginContext.hook_data>` dictionary on the context by setting :attr:`~cfngin.hook.data_key` in the :class:`~cfngin.hook` config.

This lookup lets you look up values in that dictionary.
A good example of this is when you use the :ref:`aws_lambda hook` to upload AWS Lambda code, then need to pass that code object as the **Code** variable in a Blueprint.

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- region

.. rubric:: Example
.. code-block:: yaml

  # If you set the ``data_key`` config on the aws_lambda hook to be "myfunction"
  # and you name the function package "TheCode" you can get the troposphere
  # awslambda.Code object with:

  Code: ${hook_data myfunction.TheCode}

  # If you need to pass the code location as individual strings for use in a
  # CloudFormation template instead of a Blueprint, you can do so like this:

  Bucket: ${hook_data myfunction.TheCode::load=troposphere, get=S3Bucket}
  Key: ${hook_data myfunction.TheCode::load=troposphere, get=S3Key}

.. versionchanged:: 2.0.0
  Support for the syntax deprecated in *1.5.0* has been removed.

.. versionchanged:: 1.5.0
  The ``<hook_name>::<key>`` syntax was deprecated with support being added for the ``key.nested_key`` syntax for accessing data within a dictionary.


----


.. _`custom lookup`:

*************
Custom Lookup
*************

A custom lookup may be registered within the config.
For more information see :attr:`~cfngin.config.lookups`.


Writing A Custom Lookup
=======================

A custom lookup must be in an executable, importable python package or standalone file.
The lookup must be importable using your current ``sys.path``.
This takes into account the :attr:`~cfngin.config.sys_path` defined in the config file as well as any ``paths`` of :class:`~cfngin.package_sources`.

The lookup must be a subclass of :class:`~runway.lookups.handlers.base.LookupHandler` with a ``@classmethod`` of ``handle`` with a similar signature to what is provided in the example below.
There must be only one lookup per file.
The file containing the lookup class must have a ``TYPE_NAME`` global variable with a value of the name that will be used to register the lookup.

The lookup must return a string if being used for a CloudFormation parameter.

If using boto3 in a lookup, use :meth:`context.get_session() <runway.context.CfnginContext.get_session>` instead of creating a new session to ensure the correct credentials are used.


.. rubric:: Example
.. code-block:: python

  """Example lookup."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, Any, Optional, Union

  from runway.cfngin.utils import read_value_from_path
  from runway.lookups.handlers.base import LookupHandler

  if TYPE_CHECKING:
      from runway.cfngin.providers.aws.default import Provider
      from runway.context import CfnginContext, RunwayContext

  TYPE_NAME = "mylookup"


  class MylookupLookup(LookupHandler):
      """My lookup."""

      @classmethod
      def handle(
          cls,
          value: str,
          context: Union[CfnginContext, RunwayContext],
          *_args: Any,
          provider: Optional[Provider] = None,
          **_kwargs: Any
      ) -> str:
          """Do something.

          Args:
              value: Value to resolve.
              context: The current context object.
              provider: CFNgin AWS provider.

          """
          query, args = cls.parse(read_value_from_path(value))

          # example of using get_session for a boto3 session
          s3_client = context.get_session().client("s3")

          return "something"
