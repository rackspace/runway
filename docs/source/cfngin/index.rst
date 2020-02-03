.. _Blueprints: ../terminology.html#blueprint
.. _Stacker: https://github.com/cloudtools/stacker
.. _troposphere: https://github.com/cloudtools/troposphere

CFNgin
======

CFNgin is a library used to create & update multiple CloudFormation stacks.
It originates from the open source library `Stacker`_ and has been adapted to better fit Runway.
Since we originally cloned the `Stacker`_ repo, we have continued development to improve what they started.

CFNgin Blueprints_ are written in troposphere_, though the purpose of most templates is to keep them as generic as possible and then use configuration to modify them.


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
