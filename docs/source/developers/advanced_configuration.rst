######################
Advanced Configuration
######################

This section has been placed in the **Developer Guide** because it details advanced configuration that should only be used by those with intimate knowledge of how Runway works.


*********************
Environment Variables
*********************

Environment variables can be used to alter the functionality of Runway.

**CI (Any)**
    If not ``undefined``, Runway will operate in non-iterative mode,

**DEBUG (Any)**
    If not ``undefined``, debug logs will be shown.

**DEPLOY_ENVIRONMENT (str)**
    Explicitly define the deploy environment.

**CFNGIN_STACK_POLL_TIME (int)**
    Number of seconds between CloudFormation API calls. Adjusting this will
    impact API throttling. (`default:` ``30``)

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
