.. _`default lookup`:

#######
default
#######

:Query Syntax: ``<env_var>::<default value>``


The default_ lookup type will check if a value exists for the variable in the environment file, then fall back to a default defined in the CFNgin config if the environment file doesn't contain the variable.
This allows defaults to be set at the config file level, while granting the user the ability to override that value per environment.


.. note::
  The default_ lookup only supports checking if a variable is defined in an environment file.
  It does not support other embedded lookups to see if they exist.
  Only checking variables in the environment file are supported.
  If you attempt to have the default lookup perform any other lookup that fails, CFNgin will throw an exception for that lookup and will exit before it gets a chance to fall back to the default in your config.



*******
Example
*******

.. code-block:: yaml

  Groups: ${default app_security_groups::sg-12345,sg-67890}

If ``app_security_groups`` is defined in the environment file, its defined value will be returned. Otherwise, ``sg-12345,sg-67890`` will be the returned value.
