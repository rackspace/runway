"""Used to plan actions by comparing what is live and what is defined locally.

.. note:: Currently only supported for `AWS CDK`_, `CloudFormation`_,
          `Terraform`_, and `Troposphere`_.

When run, the environment is determined from the current git branch
unless ``ignore_git_branch: true`` is specified in the
:ref:`Runway config file<runway-config>`. If the ``DEPLOY_ENVIRONMENT``
environment variable is set, it's value will be used. If neither the git
branch or environment variable are available, the directory name is used.
The environment identified here is used to determine the env/config files
to use. It is also used with options defined in the Runway config file
such as ``assume_role``, ``account_id``, etc. See
:ref:`Runway Config<runway-config>` for details on these options.

The user will be prompted to select which
:ref:`deployment(s)<runway-deployment>` and
:ref:`module(s)<runway-module>` to process unless there is only one
:ref:`deployment<runway-deployment>` and/or
:ref:`module<runway-module>`, the environment variable ``CI`` is set,
or the ``--tag <tag>...`` option provided is used. In which case, the
:ref:`deployment(s)<runway-deployment>` and :ref:`module(s)<runway-module>`
will be processed in sequence, in the order they are defined.

.. rubric:: Options

+--------------------+-------------------------------------------------+
| ``--tag <tag>...`` | | Select modules for processing by tag or tags. |
|                    |   This option can be specified                  |
|                    | | more than once to build a list of tags that   |
|                    |   are treated as "AND".                         |
|                    | | (ex. ``--tag <tag1> --tag <tag2>`` would      |
|                    |   select all modules with BOTH tags).           |
+--------------------+-------------------------------------------------+

.. rubric:: Equivalent To

There are the native commands that are used:

- ``cdk diff`` - https://docs.aws.amazon.com/cdk/latest/guide/tools.html
- ``stacker diff`` -
  https://stacker.readthedocs.io/en/stable/commands.html#diff
- ``terraform plan`` - https://www.terraform.io/docs/commands/plan.html

.. rubric:: Example

.. code-block:: shell

    $ runway plan

"""
from ..modules_command import ModulesCommand


class Plan(ModulesCommand):
    """Extend ModulesCommand with execute to run the plan method."""

    def execute(self):
        """Generate plans."""
        self.run(deployments=None, command='plan')
