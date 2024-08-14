.. _cfngin_remote_sources:

##############
Remote Sources
##############

The :attr:`~cfngin.config.package_sources` field can be used to define additional locations to include when processing a configuration file.
The locations can either be a local file path or a network accessible location.

By defining these additional sources you are able to extend your *$PATH* to make more resources accessible or even merge multiple configuration files into the current configuration file.

.. class:: cfngin.package_sources

  There are three different types of package sources - git repository, local, and AWS S3.

  .. attribute:: git
    :type: Optional[List[cfngin.package_source.git]]
    :value: []

    A list of git repositories to include when processing the configuration file.

    See `Git Repository`_ for detailed information.

    .. rubric: Example
    .. code-block:: yaml

      package_sources:
        git:
          ...

  .. attribute:: local
    :type: Optional[List[cfngin.package_source.local]]
    :value: []

    A list of additional local directories to include when processing the configuration file.

    See Local_ for detailed information.

    .. rubric: Example
    .. code-block:: yaml

      package_sources:
        local:
          ...

  .. attribute:: s3
    :type: Optional[List[cfngin.package_source.s3]]
    :value: []

    A list of AWS S3 objects to include when processing the configuration file.

    See `AWS S3`_ for detailed information.

    .. rubric: Example
    .. code-block:: yaml

      package_sources:
        s3:
          ...



**************
Git Repository
**************

.. class:: cfngin.package_source.git

  Package source located in a git repository.

  Cloned repositories are cached locally between runs.
  The cache location is defined by :attr:`cfngin.config.cfngin_cache_dir`.

  .. attribute:: branch
    :type: Optional[str]
    :value: None

    Name of a branch to checkout after cloning the git repository.

    Only one of :attr:`~cfngin.package_source.git.branch`, :attr:`~cfngin.package_source.git.commit`, or :attr:`~cfngin.package_source.git.tag` can be defined.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - branch: master

  .. attribute:: commit
    :type: Optional[str]
    :value: None

    After cloning the git repository, reset *HEAD* to the given commit hash.

    Only one of :attr:`~cfngin.package_source.git.branch`, :attr:`~cfngin.package_source.git.commit`, or :attr:`~cfngin.package_source.git.tag` can be defined.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - commit: 5d83f7ff1ad6527233be2c27e9f68816599b6c57

  .. attribute:: configs
    :type: Optional[List[str]]
    :value: []

    Configuration files from this source location can also be used by specifying a list of file paths.

    These configuration files are merged into the current configuration file with the current file taking precedence.
    When using this usage pattern, it is advised to use dictionary definitions for everything that supports it to allow for granular overriding.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - configs:
            - example-01.yml
            - example-02.yml

  .. attribute:: paths
    :type: Optional[List[str]]
    :value: []

    A list of subdirectories within the source location that should be added to *$PATH*.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - paths:
            - some/directory/
            - another/

  .. attribute:: tag
    :type: Optional[str]
    :value: None

    After cloning the git repository, reset *HEAD* to the given tag.

    Only one of :attr:`~cfngin.package_source.git.branch`, :attr:`~cfngin.package_source.git.commit`, or :attr:`~cfngin.package_source.git.tag` can be defined.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - tag: v1.0.0

  .. attribute:: uri
    :type: str

    The protocol and URI address of the git repository.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        git:
          - uri: git@github.com:onicagroup/runway.git  # ssh
          - uri: https://github.com/onicagroup/runway.git  # https


*****
Local
*****

.. class:: cfngin.package_source.local

  Package source located on a local disk.

  .. attribute:: configs
    :type: Optional[List[str]]
    :value: []

    Configuration files from this source location can also be used by specifying a list of file paths.

    These configuration files are merged into the current configuration file with the current file taking precedence.
    When using this usage pattern, it is advised to use dictionary definitions for everything that supports it to allow for granular overriding.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        local:
          - configs:
            - example-01.yml
            - example-02.yml

  .. attribute:: paths
    :type: Optional[List[str]]
    :value: []

    A list of subdirectories within the source location that should be added to *$PATH*.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        local:
          - paths:
            - some/directory/
            - another/

  .. attribute:: source
    :type: str

    Path relative to the current configuration file that is the root of the local package source.
    Can also be provided as an absolute path but this is not recommended as it will be bound to your system.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        local:
          - source: ./../example_code


******
AWS S3
******

.. class:: cfngin.package_source.s3

  Package source located in AWS S3.

  S3 objects are cached locally between runs.
  The cache location is defined by :attr:`cfngin.config.cfngin_cache_dir`.

  .. attribute:: bucket
    :type: str

    Name of the AWS S3 bucket.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        s3:
          - bucket: example-bucket

  .. attribute:: configs
    :type: Optional[List[str]]
    :value: []

    Configuration files from this source location can also be used by specifying a list of file paths.

    These configuration files are merged into the current configuration file with the current file taking precedence.
    When using this usage pattern, it is advised to use dictionary definitions for everything that supports it to allow for granular overriding.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        s3:
          - configs:
            - example-01.yml
            - example-02.yml

  .. attribute:: key
    :type: str

    Key for an S3 object within the :attr:`~cfngin.package_source.s3.bucket`.
    The object should be an archived file that can be unzipped.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
          s3:
            - key: path/to/example.zip

  .. attribute:: paths
    :type: Optional[List[str]]
    :value: []

    A list of subdirectories within the source location that should be added to *$PATH*.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        s3:
          - paths:
            - some/directory/
            - another/

  .. attribute:: requester_pays
    :type: Optional[bool]
    :value: False

    Confirms that the requester knows that they will be charged for the request

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        s3:
          - requester_pays: true

  .. attribute:: use_latest
    :type: Optional[bool]
    :value: True

    Update the local copy if the last modified date in AWS S3 changes.

    .. rubric:: Example
    .. code-block:: yaml

      package_sources:
        s3:
          - use_latest: true
