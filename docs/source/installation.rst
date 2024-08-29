############
Installation
############


Runway can be installed like any other Python package, but we instead strongly recommend using it per-project with :link:`poetry`.
See `Why Version Lock Per-Project`_ for more info regarding this suggestion.

.. tab-set::

  .. tab-item:: poetry (recommended)
    :sync: poetry

    .. code-block:: console

      $ poetry add runway

  .. tab-item:: pip
    :sync: pip

    .. code-block:: console

      $ pip install --user runway
      # or (depending on how Python was installed)
      $ pip install runway

.. rubric:: Usage

.. tab-set::

  .. tab-item:: poetry
    :sync: poetry

    .. code-block:: console

      $ poetry run runway --help

  .. tab-item:: pip
    :sync: pip

    .. code-block:: console

      $ runway --help


.. versionremoved:: 2.8.0
  Support for installation via cURL and npm was removed.
  Prior versions published to npm will remain, in a deprecated/unsupported state, indefinably.
  Prior versions published to S3 will be removed at a date yet to be determined.



****************************
Why Version Lock Per-Project
****************************

Locking the version of Runway per-project will allow you to:

- Specify the version(s) of Runway compatible with your deployments config
- Ensure Runway executions are performed with the same version (regardless of
  where/when they occur -- avoids the dreaded "works on my machine")
