#############################
keypair.ensure_keypair_exists
#############################

:Hook Path: ``runway.cfngin.hooks.keypair.ensure_keypair_exists``


Ensure a specific keypair exists within AWS. If the key doesn't exist, upload it.



****
Args
****

.. data:: keypair
  :type: str
  :noindex:

  Name of the key pair to create

.. data:: public_key_path
  :type: str | None
  :value: None
  :noindex:

  Path to a public key file to be imported instead of generating a new key.
  Incompatible with the SSM options, as the private key will not be available for storing.

.. data:: ssm_key_id
  :type: str | None
  :value: None
  :noindex:

  ID of a KMS key to encrypt the SSM
  parameter with. If omitted, the default key will be used.

.. data:: ssm_parameter_name
  :type: str | None
  :value: None
  :noindex:

  Path to an SSM store parameter to receive the generated private key, instead of importing it or storing it locally.
