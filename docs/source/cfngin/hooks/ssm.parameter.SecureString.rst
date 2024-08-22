##########################
ssm.parameter.SecureString
##########################

:Hook Path: :class:`runway.cfngin.hooks.ssm.parameter.SecureString`


Create, update, and delete a **SecureString** SSM parameter.

A SecureString parameter is any sensitive data that needs to be stored and referenced in a secure manner.
If you have data that you don't want users to alter or reference in plaintext, such as passwords or license keys, create those parameters using the SecureString datatype.

When used in the :attr:`~cfngin.config.pre_deploy` or :attr:`~cfngin.config.post_deploy` stage this hook will create or update an SSM parameter.

When used in the :attr:`~cfngin.config.pre_destroy` or :attr:`~cfngin.config.post_destroy` stage this hook will delete an SSM parameter.


.. versionadded:: 2.2.0



****
Args
****

.. data:: allowed_pattern
  :type: str | None
  :value: None
  :noindex:

  A regular expression used to validate the parameter value.

.. data:: data_type
  :type: Literal["aws:ec2:image", "text"] | None
  :value: None
  :noindex:

  The data type for a String parameter.
  Supported data types include plain text and Amazon Machine Image IDs.

.. data:: description
  :type: str | None
  :value: None
  :noindex:

  Information about the parameter.

.. data:: force
  :type: bool
  :value: False
  :noindex:

  Skip checking the current value of the parameter, just put it.
  Can be used alongside **overwrite** to always update a parameter.

.. data:: key_id
  :type: str | None
  :value: None
  :noindex:

  The KMS Key ID that you want to use to encrypt a parameter.
  Either the default AWS Key Management Service (AWS KMS) key automatically assigned to your AWS account or a custom key.

.. data:: name
  :type: str
  :noindex:

  The fully qualified name of the parameter that you want to add to the system.

.. data:: overwrite
  :type: bool
  :value: True
  :noindex:

  Allow overwriting an existing parameter.
  If this is set to ``False`` and the parameter already exists, the parameter will not be updated and a warning will be logged.

.. data:: policies
  :type: list[dict[str, Any]] | str | None
  :value: None
  :noindex:

  One or more policies to apply to a parameter.
  This field takes a JSON array.

.. data:: tags
  :type: dict[str, str] | list[TagTypeDef] | None
  :value: None
  :noindex:

  Tags to be applied to the parameter.

.. data:: tier
  :type: Literal["Advanced", "Intelligent-Tiering", "Standard"]
  :value: "Standard"
  :noindex:

  The parameter tier to assign to a parameter.

.. data:: value
  :type: str | None
  :value: None
  :noindex:

  The parameter value that you want to add to the system.
  Standard parameters have a value limit of 4 KB.
  Advanced parameters have a value limit of 8 KB.

  If the value of this field is falsy, the parameter will not be created or updated.

  If the value of this field matches what is already in SSM Parameter Store, it will not be updated unless **force** is ``True``.



*******
Example
*******

.. code-block:: yaml

  pre_deploy: &hooks
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/foo
        value: bar
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/parameter1
        description: This is an example.
        tags:
          tag-key: tag-value
        tier: Advanced
        value: ${value_may_be_none}
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /example/parameter2
        policies:
          - Type: Expiration
            Version: 1.0
            Attributes:
              Timestamp: 2018-12-02T21:34:33.000Z
        tags:
          - Key: tag-key
            Value: tag-value
        value: ${something_else}

  post_destroy: *hooks
