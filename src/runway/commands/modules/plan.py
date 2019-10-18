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

Plan will always be run against all deployments for the determined
environment.

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
