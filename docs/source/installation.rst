Installation
============

Installing Runway
^^^^^^^^^^^^^^^^^

Runway runs on Python 2.7 and Python 3.5+. It is also packaged as a
single-binary bundled with python for distribution through non-python
package managers.

Runway is hosted on PyPI and npm as the package named ``runway``.
It can be installed like any other Python or Node package.
We strongly recommend locking the version per-project.
For Python, this can be done with `pipenv <https://pypi.org/project/pipenv/>`_.


Version Locking with Pipenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Why
~~~

After installing pipenv (e.g. ``pip install --user pipenv``), placing
``Pipfile``/``Pipfile.lock`` files alongside your ``runway.yml`` will allow
you to:

- Specify the version(s) of runway compatible with your deployments config
- Ensure runway executions are performed with the same version (regardless of
  where/when they occur -- avoids the dreaded "works on my machine")

How
~~~

In your project's directory, execute ``pipenv install runway``. This will:

#. Update (creating if missing) a ``Pipfile`` file with your project's runway
   dependency
#. Create a Python virtual environment (hidden in your user profile folder)
   dedicated to your project, with runway installed in it
#. Update (creating if missing) a ``Pipfile.lock`` file containing the exact
   versions/crypto-hashes of runway (and dependencies) installed in your
   python virtual environment

Now runway can be used in the project via ``pipenv run runway ...``
(e.g. ``pipenv run runway takeoff``).

To ensure future users of the project use the same version of runway,
direct them (e.g. via a Makefile) to invoke it via
``pipenv sync; pipenv run runway ...`` -- this will ensure the version in
their virtual environment is kept in sync with the project's lock file.

Troubleshooting
^^^^^^^^^^^^^^^

Pipenv Not Found
~~~~~~~~~~~~~~~~

If pipenv isn't available after installation (via
``pip install --user pipenv``, see the :ref:`python-setup` guide.
