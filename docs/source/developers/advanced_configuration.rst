######################
Advanced Configuration
######################

This section has been placed in the **Developer Guide** because it details advanced configuration that should only be used by those with intimate knowledge of how Runway works.


*********************
Environment Variables
*********************

Environment variables can be used to alter the functionality of Runway.

.. data:: CI
  :type: Any
  :noindex:

  If not *undefined*, Runway will operate in non-iterative mode.

.. data:: DEBUG
  :type: int
  :value: 0
  :noindex:

  Used to select the debug logs to display

  - ``0`` or not defined with show no debug logs
  - ``1`` will show Runway's debug logs
  - ``2`` will show Runway's debug logs and some dependency debug logs (e.g. botocore)

  .. versionadded:: 1.10.0

.. data:: DEPLOY_ENVIRONMENT
  :type: str
  :noindex:

  Explicitly define the deploy environment.

  .. versionadded:: 1.3.4

.. data:: CFNGIN_STACK_POLL_TIME
  :type: int
  :value: 30
  :noindex:

  Number of seconds between CloudFormation API calls. Adjusting this will
  impact API throttling.

.. data:: RUNWAY_COLORIZE
  :type: str
  :noindex:

  Explicitly enable/disable colorized output for :ref:`index:AWS Cloud Development Kit (CDK)`, :ref:`index:Serverless Framework`, and :ref:`index:Terraform` :term:`Modules <module>`.
  Having this set to a truthy value will prevent ``-no-color``/``--no-color`` from being added to any commands even if stdout is not a TTY.
  Having this set to a falsy value will include ``-no-color``/``--no-color`` in commands even if stdout is a TTY.
  If the IaC tool has other mechanisms for disabling color output, using a truthy value will not circumvent them.

  Truthy values are ``y``, ``yes``, ``t``, ``true``, ``on`` and ``1``.
  Falsy values are ``n``, ``no``, ``f``, ``false``, ``off`` and ``0``.
  Raises :exc:`ValueError` if anything else is used.

  .. versionadded:: 1.8.1

.. data:: RUNWAY_MAX_CONCURRENT_MODULES
  :type: int
  :noindex:

  Max number of modules that can be deployed to concurrently.
  (`default:` ``min(61, os.cpu_count())``)

  On Windows, this must be equal to or lower than ``61``.

  **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
  together, please consider the nature of their relationship when
  manually setting this value. (``parallel_regions * child_modules``)

  .. versionadded:: 1.4.3

.. data:: RUNWAY_MAX_CONCURRENT_REGIONS
  :type: int
  :noindex:

  Max number of regions that can be deployed to concurrently.
  (`default:` ``min(61, os.cpu_count())``)

  On Windows, this must be equal to or lower than ``61``.

  **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
  together, please consider the nature of their relationship when
  manually setting this value. (``parallel_regions * child_modules``)

  .. versionadded:: 1.4.3

.. data:: RUNWAY_LOG_FIELD_STYLES
  :type: str
  :noindex:

  Can be provided to customize the styling (color, bold, etc) used for `LogRecord attributes`_ (except for message).
  By default, Runway does not apply style to fields.
  For information on how to format the value, see the documentation provided by coloredlogs_.

  .. versionadded:: 1.10.0

.. data:: RUNWAY_LOG_FORMAT
  :type: str
  :noindex:

  Can be provided to use a custom log message format.
  The value should be a format string using %-formatting.
  In addition to being able to use `LogRecord attributes`_ in the string, Runway provides the additional fields of ``%(hostname)s`` and ``%(programname)s``.

  If not provided, ``[%(programname)s] %(message)s`` is used unless using debug, verbose or no color.
  In that case, ``%(levelname)s:%(name)s:%(message)s`` is used.

  .. versionadded:: 1.10.0

.. data:: RUNWAY_LOG_LEVEL_STYLES
  :type: str
  :noindex:

  Can be provided to customize the styling (color, bold, etc) used for log messages sent to each log level.
  If provided, the parsed value will be merged with Runway's default styling.
  For information on how to format the value, see the documentation provided by coloredlogs_.

  .. versionadded:: 1.10.0

.. data:: RUNWAY_NO_COLOR
  :type: Any
  :noindex:

  Disable Runway's colorized logs.
  Providing this will also change the log format to ``%(levelname)s:%(name)s:%(message)s``.

  .. versionadded:: 1.8.1

.. data:: VERBOSE
  :type: Any
  :noindex:

  If not *undefined*, Runway will display verbose logs and change the logging format to ``%(levelname)s:%(name)s:%(message)s``.

  .. versionadded:: 1.10.0

.. _LogRecord attributes: https://docs.python.org/3/library/logging.html#logrecord-attributes
.. _coloredlogs: https://coloredlogs.readthedocs.io/en/latest/api.html#changing-the-colors-styles
