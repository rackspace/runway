###
kms
###

:Query Syntax: ``<encrypted-blob>[::region=<region>, ...]``


The kms_ lookup type decrypts its input value.

As an example, if you have a database and it has a parameter called ``DBPassword`` that you don't want to store in plain text in your config (maybe because you want to check it into your version control system to share with the team), you could instead en
crypt the value using ``kms``.


.. versionchanged:: 2.7.0
  The ``[<region>@]<encrypted-blob>`` syntax is deprecated to comply with Runway's lookup syntax.



*********
Arguments
*********

This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- default



*******
Example
*******

We use can use the aws cli to get the encrypted value for the string "PASSWORD" using the master key called 'myKey' in us-east-1.

.. code-block:: console

  $ aws --region us-east-1 kms encrypt --key-id alias/myKey \
      --plaintext "PASSWORD" --output text --query CiphertextBlob

  CiD6bC8t2Y<...encrypted blob...>

.. code-block:: yaml

  namespace: example

  stacks:
    - ...
      variables:
        # With CFNgin we would reference the encrypted value like:
        DBPassword: ${kms CiD6bC8t2Y<...encrypted blob...>::region=us-east-1}
        # The above would resolve to:
        DBPassword: PASSWORD

This requires that the credentials used by CFNgin have access to the master key used to encrypt the value.

It is also possible to store the encrypted blob in a file (useful if the value is large) using the ``file://`` prefix, ie:

.. code-block:: yaml

  namespace: example

  stacks:
    - ...
      variables:
        DockerConfig: ${kms file://dockercfg}

.. note::
  Lookups resolve the path specified with ``file://`` relative to the location of the config file, not the current working directory.
