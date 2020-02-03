.. _CFNgin API Docs: ../apidocs/runway.cfngin.html
.. _Stacker: https://github.com/cloudtools/stacker

Migrating from Stacker to CFNgin
================================

.. important:: Most current uses of runway with Stacker_ will continue to work.
               But, for imports from Stacker_, Runway will automatically redirect them to CFNgin.
               Because of this, you may experience errors depending on how you are consuming the Stacker_ components.
               This "shim" will remain in place until the release of Runway 2.0.0, no sooner then 2020-12.

All components available in Stacker_ 1.7.0 are available in CFNgin at the same path within ``runway.cfngin``.

.. rubric:: Blueprint Example
.. code-block:: python

    # what use to be this
    from stacker.blueprints.base import Blueprint
    from stacker.blueprints.variables.types import CFNString

    # now becomes this
    from runway.cfngin.blueprints.base import Blueprint
    from runway.cfngin.blueprints.variables.types import CFNString

.. rubric:: Hook Example
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

.. seealso:: `CFNgin API Docs`_
