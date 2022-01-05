###
kms
###

:Query Syntax: ``[<region>@]<encrypted-blob>``


The kms_ lookup type decrypts its input value.

As an example, if you have a database and it has a parameter called ``DBPassword`` that you don't want to store in plain text in your config (maybe because you want to check it into your version control system to share with the team), you could instead encrypt the value using ``kms``.



*******
Example
*******

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
