How To Use
==========

Getting Started
^^^^^^^^^^^^^^^
- Structure your project repo with environments & modules (see
  :ref:`repo-structure` )
- Create a ``runway.yml`` file at the root of each environment. Most options
  detailed in :ref:`runway-config-options` are not required. E.g., the
  following is sufficient to deploy the module in
  ``nameofmycloudformationfolder.cfn`` to us-west-2:

::

    ---
    deployments:
      - modules:
          - nameofmycloudformationfolder.cfn
        regions:
          - us-west-2

- Define per-environment config options/enablement for each module (see
  :ref:`module-configurations` )

Basic Deployment Commands
^^^^^^^^^^^^^^^^^^^^^^^^^
- ``runway test`` (aka ``runway preflight``) - execute this in your environment to catch errors; if it exits ``0``, you're ready for...
- ``runway plan`` (aka ``runway taxi``) - this optional step will show the diff/plan of what will be changed. With a satisfactory plan you can...
- ``runway deploy`` (aka ``runway takeoff``) - if running interactively, you can choose which deployment to run; otherwise (i.e. on your CI system) each deployment will be run in sequence.

Removing Deployments
^^^^^^^^^^^^^^^^^^^^
- ``runway destroy`` (aka ``runway dismantle``) - if running interactively, you can choose which deployment to remove; otherwise (i.e. on your CI system) every deployment will be run in reverse sequence (use with caution).
