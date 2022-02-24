.. _random.string lookup:

#############
random.string
#############

:Query Syntax: ``<desired-length>[::<arg>=<arg-val>, ...]``


Generate a random string of the given length.


.. versionadded:: 2.2.0



*********
Arguments
*********

.. data:: digits
  :type: bool
  :value: True
  :noindex:

  When generating the random string, the string may contain digits (``[0-9]``).
  If the string can contain digits, it will always contain at least one.

.. data:: lowercase
  :type: bool
  :value: True
  :noindex:

  When generating the random string, the string may contain lowercase letters (``[a-z]``).
  If the string can contain lowercase letters, it will always contain at least one.

.. data:: punctuation
  :type: bool
  :value: False
  :noindex:

  When generating the random string, the string may contain ASCII punctuation (``[!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~]``).
  If the string can contain ASCII punctuation, it will always contain at least one.

.. data:: uppercase
  :type: bool
  :value: True
  :noindex:

  When generating the random string, the string may contain uppercase letters (``[A-Z]``).
  If the string can contain uppercase letters, it will always contain at least one.


This Lookup supports all :ref:`Common Lookup Arguments` but, the following have limited or no effect:

- default
- get
- indent
- load
- region



*******
Example
*******

This example shows the use of this lookup to create an SSM parameter that will retain value generated during the first deployment.
Even through subsequent deployments generate a new value that is passed to the hook, the hook does not overwrite the value of an existing parameter.

.. code-block:: yaml

  pre_deploy: &hooks
    - path: runway.cfngin.hooks.ssm.parameter.SecureString
      args:
        name: /${namespace}/password
        overwrite: false
        value: ${random.string 12::punctuation=true}

  post_destroy: *hooks
