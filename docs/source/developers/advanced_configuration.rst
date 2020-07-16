######################
Advanced Configuration
######################

This section has been placed in the **Developer Guide** because it details advanced configuration that should only be used by those with intimate knowledge of how Runway works.


*********************
Environment Variables
*********************

Environment variables can be used to alter the functionality of Runway.

**CI (Any)**
  If not ``undefined``, Runway will operate in non-iterative mode.

**DEBUG (int)**
  Used to select the debug logs to display

  - ``0`` or not defined with show no debug logs
  - ``1`` will show Runway's debug logs
  - ``2`` will show Runway's debug logs and some dependency debug logs (e.g. botocore)

**DEPLOY_ENVIRONMENT (str)**
  Explicitly define the deploy environment.

**CFNGIN_STACK_POLL_TIME (int)**
  Number of seconds between CloudFormation API calls. Adjusting this will
  impact API throttling. (`default:` ``30``)

**RUNWAY_COLORIZE (str)**
  Explicitly enable/disable colorized output for :ref:`CDK <mod-cdk>`, :ref:`Serverless <mod-sls>`, and :ref:`Terraform <mod-tf>` modules.
  Having this set to a truthy value will prevent ``-no-color``/``--no-color`` from being added to any commands even if stdout is not a TTY.
  Having this set to a falsy value will include ``-no-color``/``--no-color`` in commands even if stdout is a TTY.
  If the IaC tool has other mechanisms for disabling color output, using a truthy value will not circumvent them.

  Truthy values are ``y``, ``yes``, ``t``, ``true``, ``on`` and ``1``.
  Falsy values are ``n``, ``no``, ``f``, ``false``, ``off`` and ``0``.
  Raises :exc:`ValueError` if anything else is used.

**RUNWAY_MAX_CONCURRENT_MODULES (int)**
  Max number of modules that can be deployed to concurrently.
  (`default:` ``min(61, os.cpu_count())``)

  On Windows, this must be equal to or lower than ``61``.

  **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
  together, please consider the nature of their relationship when
  manually setting this value. (``parallel_regions * child_modules``)

**RUNWAY_MAX_CONCURRENT_REGIONS (int)**
  Max number of regions that can be deployed to concurrently.
  (`default:` ``min(61, os.cpu_count())``)

  On Windows, this must be equal to or lower than ``61``.

  **IMPORTANT:** When using ``parallel_regions`` and ``child_modules``
  together, please consider the nature of their relationship when
  manually setting this value. (``parallel_regions * child_modules``)

**RUNWAY_LOG_FIELD_STYLES (str)**
  Can be provided to customize the styling (color, bold, etc) used for `LogRecord attributes`_ (except for message).
  By default, Runway does not apply style to fields.
  For information on how to format the value, see the documentation provided by coloredlogs_.

**RUNWAY_LOG_FORMAT (str)**
  Can be provided to use a custom log message format.
  The value should be a format string using %-formatting.
  In addition to being able to use `LogRecord attributes`_ in the string, Runway provides the additional fields of ``%(hostname)s`` and ``%(programname)s``.

  If not provided, ``[%(programname)s] %(message)s`` is used unless using debug, verbose or no color.
  In that case, ``%(levelname)s:%(name)s:%(message)s`` is used.

**RUNWAY_LOG_LEVEL_STYLES (str)**
  Can be provided to customize the styling (color, bold, etc) used for log messages sent to each log level.
  If provided, the parsed value will be merged with Runway's default styling.
  For information on how to format the value, see the documentation provided by coloredlogs_.

**RUNWAY_NO_COLOR (Any)**
  Disable Runway's colorized logs.
  Providing this will also change the log format to ``%(levelname)s:%(name)s:%(message)s``.

**VERBOSE (Any)**
  If not ``undefined``, Runway will display verbose logs and change the logging format to ``%(levelname)s:%(name)s:%(message)s``.

.. _LogRecord attributes: https://docs.python.org/3/library/logging.html#logrecord-attributes
.. _coloredlogs: https://coloredlogs.readthedocs.io/en/latest/api.html#changing-the-colors-styles
