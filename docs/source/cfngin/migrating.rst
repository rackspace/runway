.. _Stacker: https://github.com/cloudtools/stacker

######################
Migrating from Stacker
######################

.. important:: Most current uses of Runway with Stacker_ will continue to work.
               But, for imports from Stacker_, Runway will automatically redirect them to CFNgin.
               Because of this, you may experience errors depending on how you are consuming the Stacker_ components.
               This "shim" will remain in place until the release of Runway 2.0.0, no sooner then 2020-12.


**********
Blueprints
**********

All components available in Stacker_ 1.7.0 are available in Runway's CFNgin at the same path within ``runway.cfngin``.

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

.. important:: The Stacker keys can still be used with Runway's CFNgin for the time being.
               This will remain in place until the release of Runway 2.0.0, no sooner then 2020-12.

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

.. rubric:: Example Definition
.. code-block:: yaml

    pre_build:
      what_use_to_be_this:
        path: stacker.hooks.commands.run_command
        args:
          command: echo "Hello $USER!"
      now_becomes_this:
        path: runway.cfngin.hooks.commands.run_command
        args:
          command: echo "Hello $USER!"

.. seealso:: `CFNgin API Docs <../apidocs/runway.cfngin.html>`__


Custom Lookups
==============

See the :ref:`Custom Lookups <custom lookup>` section of the docs for detailed instructions on how lookups should be written.

.. important:: Stacker lookups (function and class styles) are supported for the time being.
               It is recommended to update them to the Runway's CFNgin format outlined in :ref:`Custom Lookups <custom lookup>`.
               Support for Stacker style lookups will remain in place until the release of Runway 2.0.0, no sooner then 2020-12.
