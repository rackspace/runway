######
envvar
######

.. deprecated:: 2.7.0
  Replaced by :ref:`CFNgin env lookup`


:Query Syntax: ``<variable-name>``


The envvar_ lookup type retrieves a value from a variable in the shell's environment.



*******
Example
*******

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
