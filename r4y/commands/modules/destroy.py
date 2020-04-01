"""Used to destroy :ref:`modules<r4y-module>` with Runway.

.. danger:: Use extreme caution when using with ``CI`` or
            ``--tag <tag>...``. You will **not** be prompted before
            deletion. All modules (or those selected by tag) for the
            current environment will be **irrecoverably deleted**.

When run, the environment is determined from the current git branch
unless ``ignore_git_branch: true`` is specified in the
:ref:`Runway config file<r4y-config>`. If the ``DEPLOY_ENVIRONMENT``
environment variable is set, it's value will be used. If neither the git
branch or environment variable are available, the directory name is used.
The environment identified here is used to determine the env/config files
to use. It is also used with options defined in the Runway config file
such as ``assume_role``, ``account_id``, etc. See
:ref:`Runway Config<r4y-config>` for details on these options.

The user will be prompted to select which
:ref:`deployment(s)<r4y-deployment>` and
:ref:`module(s)<r4y-module>` to process unless there is only one
:ref:`deployment<r4y-deployment>` and/or
:ref:`module<r4y-module>`, the environment variable ``CI`` is set,
or the ``--tag <tag>...`` option provided is used. In which case, the
:ref:`deployment(s)<r4y-deployment>` and :ref:`module(s)<r4y-module>`
will be processed in sequence, in reverse of the order they are defined.

.. rubric:: Options

+--------------------+-------------------------------------------------+
| ``--tag <tag>...`` | | Select modules for processing by tag or tags. |
|                    |   This option can be specified                  |
|                    | | more than once to build a list of tags that   |
|                    |   are treated as "AND".                         |
|                    | | (ex. ``--tag <tag1> --tag <tag2>`` would      |
|                    |   select all modules with BOTH tags).           |
+--------------------+-------------------------------------------------+

.. rubric:: Example

.. code-block:: shell

    # manually select deployment(s) and module(s)
    $ r4y destroy

    # select all modules with the tag 'app:example' AND 'my-tag'
    $ r4y destroy --tag app:example --tag my-tag

    # process all deployment(s) and module(s)
    $ CI=1 r4y destroy

"""
from ..modules_command import ModulesCommand


class Destroy(ModulesCommand):
    """Extend ModulesCommand with execute to run the destroy method."""

    def execute(self):
        """Destroy deployments."""
        self.run(deployments=None, command='destroy')
