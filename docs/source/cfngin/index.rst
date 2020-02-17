.. _Blueprints: ../terminology.html#blueprint
.. _Stacker: https://github.com/cloudtools/stacker
.. _troposphere: https://github.com/cloudtools/troposphere

CFNgin
======

CFNgin is a library (originating from the open source library `Stacker`_) used to create & update CloudFormation stacks.

It provides a simple way to manage stacks with features like:

- Automatic stack ordering (e.g. deploy stack "A" before stacks "B" & "C")
- Per-environment values for stack parameters
- Actions before & after stack creation/deletion


Contents:

.. toctree::
    :maxdepth: 2

    migrating
    config
    environments
    lookups
    hooks
    blueprints
    templates
