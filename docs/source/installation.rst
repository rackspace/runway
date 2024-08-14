.. _install:

############
Installation
############

To enable Runway to conform to our users' varying use cases, we have made it
available via three different install methods - `cURL`_, `npm`_, and `pip`_.


.. _install-curl:

****
cURL
****

Arguably the easiest way to install Runway is by using curl. Use one of the
endpoints below to download a single-binary executable version of Runway based
on your operating system.

+------------------+---------------------------------------------------+
| Operating System | Endpoint                                          |
+==================+===================================================+
| Linux            | https://oni.ca/runway/latest/linux                |
+------------------+---------------------------------------------------+
| macOS            | https://oni.ca/runway/latest/osx                  |
+------------------+---------------------------------------------------+
| Windows          | https://oni.ca/runway/latest/windows              |
+------------------+---------------------------------------------------+

.. tab-set::

  .. tab-item:: Linux

    .. code-block:: sh

      curl -L https://oni.ca/runway/latest/linux -o runway

  .. tab-item:: macOS

    .. code-block:: sh

        curl -L https://oni.ca/runway/latest/osx -o runway

  .. tab-item:: Windows

    .. code-block:: powershell

      Invoke-WebRequest -Uri "https://oni.ca/runway/latest/windows" -OutFile runway

.. note:: To install a specific version of Runway, you can replace ``latest``
          with a version number.

.. rubric:: Usage

To use the single-binary, run it directly as shown below. Please note that
after download, you may need to adjust the permissions before it can be
executed. (eg. Linux/macOS:``chmod +x runway``)

.. code-block:: sh

    $ ./runway deploy

**Suggested use:** CloudFormation or Terraform projects


.. _install-npm:

***
npm
***

Runway is published on npm as ``@onica/runway``.
It currently contains binaries to support macOS, Ubuntu, and Windows.

While Runway can be installed globally like any other npm package, we strongly
recommend using it per-project as a dev dependency.
See `Why Version Lock Per-Project`_ for more info regarding this suggestion.

.. code-block:: shell

    $ npm i -D @onica/runway

.. rubric:: Usage

.. code-block:: shell

    $ npx runway deploy

**Suggested use:** Serverless or AWS CDK projects


.. _install-python:

***
pip
***

Runway runs on Python 2.7 and Python 3.5+.

Runway is hosted on PyPI as the package named ``runway``.
It can be installed like any other Python package, but we instead strongly recommend using it
per-project with `poetry <https://python-poetry.org/>`_.
See `Why Version Lock Per-Project`_ for more info regarding this suggestion.

**Suggested use:** Python projects

.. tab-set::

  .. tab-item:: poetry

    .. code-block:: sh

      poetry add runway

  .. tab-item:: pip

    .. code-block:: sh

      pip install --user runway
      # or (depending on how Python was installed)
      pip install runway

.. rubric:: Usage

.. tab-set::

  .. tab-item:: poetry

    .. code-block:: sh

      poetry run runway --help

  .. tab-item:: pip

    .. code-block:: sh

      runway --help


.. _why-version-lock:

****************************
Why Version Lock Per-Project
****************************

Locking the version of Runway per-project will allow you to:

- Specify the version(s) of Runway compatible with your deployments config
- Ensure Runway executions are performed with the same version (regardless of
  where/when they occur -- avoids the dreaded "works on my machine")
