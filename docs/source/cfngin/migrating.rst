.. _Stacker: https://github.com/cloudtools/stacker

######################
Migrating from Stacker
######################



**********
Blueprints
**********

Most components available in Stacker_ 1.7.0 are available in Runway's CFNgin at the same path within ``runway.cfngin``.

.. rubric:: Example
.. code-block:: python

    # what use to be this
    from stacker.blueprints.base import Blueprint
    from stacker.blueprints.variables.types import CFNString

    # now becomes this
    from runway.cfngin.blueprints.base import Blueprint
    from runway.cfngin.blueprints.variables.types import CFNString


************
Config Files
************

There are some config top-level keys that have changed when used Runway's CFNgin.
Below is a table of the Stacker key and what they have been changed to for Runway's CFNgin

+---------------------------+----------------------------+
| Stacker                   | Runway's CFNgin            |
+===========================+============================+
| ``stacker_bucket``        | ``cfngin_bucket``          |
+---------------------------+----------------------------+
| ``stacker_bucket_region`` | ``cfngin_bucket_region``   |
+---------------------------+----------------------------+
| ``stacker_cache_dir``     | ``cfngin_cache_dir``       |
+---------------------------+----------------------------+


Build-in Hooks
==============

All hooks available in Stacker_ 1.7.0 are available in Runway's CFNgin at the same path within ``runway.cfngin``.

.. note::
  Some hooks have different :attr:`~cfngin.hook.args` and/or altered functionality.
  It is advised to review the documentation for the hook before using it.

.. rubric:: Example Definition
.. code-block:: yaml

    pre_deploy:
      - path: stacker.hooks.commands.run_command
        args:
          command: echo "Hello $USER!"
      - path: runway.cfngin.hooks.commands.run_command
        args:
          command: echo "Hello $USER!"

.. seealso::
  :mod:`runway.cfngin`
    CFNgin documentation


Custom Lookups
==============

See the :ref:`Custom Lookups <custom lookup>` section of the docs for detailed instructions on how lookups should be written.
