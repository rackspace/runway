Installation
============

Installing runway 
^^^^^^^^^^^^^^^^^

Runway runs on Python 2.7 and Python 3.5+.

Runway is hosted on PyPI as the package named ``runway``. You can install Runway with `pip <https://pypi.org/project/pip/>`_:

``pip install runway``

It is recommended to install runway using `pipenv <https://pypi.org/project/pipenv/>`_ or `virtualenv <https://pypi.org/project/virtualenv/>`_.

How To Use
==========
- ``runway test`` (aka ``runway preflight``) - execute this in your environment to catch errors; if it exits ``0``, you're ready for...
- ``runway plan`` (aka ``runway taxi``) - this optional step will show the diff/plan of what will be changed. With a satisfactory plan you can...
- ``runway deploy`` (aka ``runway takeoff``) - if running interactively, you can choose which deployment to run; otherwise (i.e. on your CI system) each deployment will be run in sequence.

Removing Deployments
^^^^^^^^^^^^^^^^^^^^
- ``runway destroy`` (aka ``runway dismantle``) - if running interactively, you can choose which deployment to remove; otherwise (i.e. on your CI system) every deployment will be run in reverse sequence (use with caution).