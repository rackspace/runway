.. _install:

Installation
============

To enable Runway to conform to our users' varying use cases, we have made it
available via three different install methods - `cURL`_, `npm`_, and `pip`_.

.. _install-curl:


cURL
^^^^

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

.. code-block:: shell

    $ curl -L https://oni.ca/runway/latest/osx -o runway

.. note:: To install a specific version of Runway, you can replace ``latest``
          with a version number.

.. rubric:: Usage

To use the single-binary, run it directly as shown below. Please note that
after download, you may need to adjust the permissions before it can be
executed. (eg. macOS/Ubuntu:``chmod +x runway``)

.. code-block:: shell

    $ ./runway deploy

**Suggested use:** CloudFormation or Terraform projects


.. _install-npm:

npm
^^^

Runway is published on npm as ``@onica/runway``. It currently contains binaries
to support macOS, Ubuntu, and Windows.

While Runway can be installed globally like any other npm package, we strongly
recommend using it per-project as a dev dependency. See
`Why Version Lock Per-Project`_ for more info regarding this suggestion.

.. code-block:: shell

    $ npm i -D @onica/runway

.. rubric:: Usage

.. code-block:: shell

    $ npx runway deploy

**Suggested use:** Serverless or AWS CDK projects


.. _install-python:

pip
^^^

Runway runs on Python 2.7 and Python 3.5+.

Runway is hosted on PyPI as the package named ``runway``. It can be installed
like any other Python package, but we instead strongly recommend using it
per-project with `pipenv <https://pypi.org/project/pipenv/>`_. See
`Why Version Lock Per-Project`_ for more info regarding this suggestion.

**Suggested use:** Python projects


Version Locking with Pipenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your project's directory, execute ``pipenv install runway``. This will:

#. Update (creating if missing) a ``Pipfile`` file with your project's Runway
   dependency
#. Create a Python virtual environment (hidden in your user profile folder)
   dedicated to your project, with Runway installed in it
#. Update (creating if missing) a ``Pipfile.lock`` file containing the exact
   versions/crypto-hashes of Runway (and dependencies) installed in your
   python virtual environment

Now Runway can be used in the project via ``pipenv run runway ...``
(e.g. ``pipenv run runway takeoff``).

To ensure future users of the project use the same version of Runway,
direct them (e.g. via a Makefile) to invoke it via
``pipenv sync; pipenv run Runway ...`` -- this will ensure the version in
their virtual environment is kept in sync with the project's lock file.


Troubleshooting
~~~~~~~~~~~~~~~


Pipenv Not Found
----------------

If pipenv isn't available after installation (via
``pip install --user pipenv``, see the :ref:`python-setup` guide.


.. _why-version-lock:

Why Version Lock Per-Project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Locking the version of Runway per-project will allow you to:

- Specify the version(s) of Runway compatible with your deployments config
- Ensure Runway executions are performed with the same version (regardless of
  where/when they occur -- avoids the dreaded "works on my machine")
