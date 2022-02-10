####
file
####

:Query Syntax: ``<supported-codec>:<data>``


The file_ lookup type allows the loading of arbitrary data from files.
The lookup additionally supports using a **codec** to parse and/or manipulate the file contents prior to returning it.
The ``parameterized-b64`` codec is particularly useful to allow the interpolation of CloudFormation parameters in a UserData attribute of an instance or launch configuration.

If the file can be read locally, the ``<data>`` portion of the query should look something like ``file://./path/to/file``.
The ``file://`` prefix tells CFNgin that it needs to open the file located at the provide path and read it's contents before continuing.
For a relative path, it will be relative to the current working directory (usually the root of the CFNgin module being processed).

If ``<data>`` is not prefixed with ``file://``, it will be treated as the contents of the file.
This enables lookups to be chained together to retrieve data and still take advantage of a codec to further parse and/or manipulate it as needed.
For example, the value of an SSM Parameter can be parsed as ``json-parameterized`` before it is returned by the lookup with the following ``${file json-parameterized:${ssm /parameter/name}}``.



****************
Supported Codecs
****************

- **plain** - Load the contents of the file untouched. This is the only codec that should be used
  with raw Cloudformation templates (the other codecs are intended for blueprints).
- **base64** - Encode the plain text file at the given path with base64 prior
  to returning it.
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

    UserData: ${file parameterized:file://path/to/file}

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
  wrapped in ``{ "Fn::Base64": ... }``, which can be used as EC2 UserData.

  When using parameterized-b64 for UserData, you should use a parameter defined as such.

  .. code-block:: python

    from troposphere import AWSHelperFn

    "UserData": {
        "type": AWSHelperFn,
        "description": "Instance user data",
        "default": Ref("AWS::NoValue")
    }

  Then set UserData in a LaunchConfiguration or Instance to ``self.variables["UserData"]``.
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



*******
Example
*******

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
