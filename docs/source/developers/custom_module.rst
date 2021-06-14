.. _mod-custom:

#####################
Custom Plugin Support
#####################

Need to expand Runway to wrap other tools?
Yes - you can do that with custom plugin support.


********
Overview
********

Runway can import Python modules that can perform custom deployments with your own set of Runway modules.
Let's say for example you want to have Runway execute an Ansible playbook to create an EC2 security group as one of the steps in the middle of your Runway deployment list - this is possible with your own plugin.
The custom plugin support allows you to mix-and-match natively supported modules (e.g. CloudFormation, Terraform) with plugins you write providing additional support for non-native modules.
Although written in Python, these plugins can natively execute non-Python binaries.


******************
RunwayModule Class
******************

Runway provides :class:`~runway.module.base.RunwayModule` to use as the base class of all module handler classes.
This base class will give you the ability to write your own module handler class that can be added to your runway.yml deployment list (More info on runway.yml below).
There are four methods that need to be defined for the class:

**deploy**
  This method is called when ``runway deploy`` is run.

**destroy**
  This method is called when ``runway destroy`` is run.

**init**
  This method is called when ``runway init`` is run.

**plan**
  This method is called when ``runway plan`` is run.


**************
Context Object
**************

``self.ctx`` includes many helpful resources for use in your Python module.

Some notable examples are:

- ``self.ctx.env.name`` - name of the environment
- ``self.ctx.env.aws_region`` - region in which the module is being executed
- ``self.ctx.env.vars`` - OS environment variables provided to the module
- ``self.path`` - path to your Runway module folder


******************
runway.yml Example
******************

After you have written your plugin, you need to add the module ``class_path``
to your module's configuration. Below is an example ``runway.yml`` containing a
single module that looks for an Ansible playbook in a folder at the root of
your Runway environment (i.e. repo) named "security_group.ansible".

Setting ``class_path`` tells Runway to import the DeployToAWS Python class,
from a file named Ansible.py in a folder named "local_runway_extensions"
(Standard Python import conventions apply). Runway will execute the ``deploy``
function in your class when you perform a ``runway deploy`` (AKA takeoff).

.. code-block:: yaml

  deployments:
    - modules:
        - path: security_group.ansible
          class_path: local_runway_extensions.Ansible.DeployToAWS
      regions:
        - us-east-1

Below is the ``Ansible.py`` module referenced above that wraps the
``ansible-playbook`` command. It will be responsible for deploying an EC2 Security Group from the playbook
with a naming convention of ``<env>-<region>.yaml`` within a fictional
``security_group.ansible`` Runway module folder. In this example, the
``ansible-playbook`` binary would already have been installed prior to a Runway
deploy, but this example does check to see if it is installed before execution
and logs an error if not. The Runway plugin will only execute
the ansible-playbook against a ``yaml`` file associated with the environment and set for the Runway
execution and region defined in the ``runway.yml``.

Using the above ``runway.yml`` and the plugin/playbook below saved to the Runway
module folder you will only have a deployment occur in the ``dev`` environment
in ``us-east-1``.  If you decide to perform a runway deployment in the ``prod``
environment, or in a different region, the ansible-playbook deployment will be
skipped. This matches the behavior of the Runway's native modules.

.. code-block:: python

  """Ansible Plugin example for Runway."""
  from __future__ import annotations

  import logging
  import subprocess
  import sys
  from typing import TYPE_CHECKING, Dict

  from runway.module.base import RunwayModule
  from runway.utils import which

  if TYPE_CHECKING:
      from pathlib import Path

  LOGGER = logging.getLogger("runway")


  def check_for_playbook(playbook_path: Path) -> Dict[str, bool]:
      """Determine if environment/region playbook exists."""
      if playbook_path.is_file():
          LOGGER.info("Processing playbook: %s", playbook_path)
          return {"skipped_configs": False}
      LOGGER.error(
          "No playbook for this environment/region found -- looking for %s",
          playbook_path,
      )
      return {"skipped_configs": True}


  class DeployToAWS(RunwayModule):
      """Ansible Runway Module."""

      def deploy(self) -> None:
          """Run ansible-playbook."""
          if not which("ansible-playbook"):
              LOGGER.error(
                  '"ansible-playbook" not found in path or is not '
                  "executable; please ensure it is installed"
                  "correctly."
              )
              sys.exit(1)
          playbook_path = self.path / f"{self.ctx.env.name}-{self.ctx.env.aws_region}"
          response = check_for_playbook(playbook_path)
          if response["skipped_configs"]:
              return
          subprocess.check_output(["ansible-playbook", str(playbook_path)])

      def destroy(self) -> None:
          """Skip destroy."""
          LOGGER.info("destroy not currently supported for Ansible")

      def init(self) -> None:
          """Skip init."""
          LOGGER.info("init not currently supported for Ansible")

      def plan(self) -> None:
          """Skip plan."""
          LOGGER.info("plan not currently supported for Ansible")


And below is the example Ansible playbook itself, saved as ``dev-us-east-1.yaml`` in the security_group.ansible folder:

.. code-block:: yaml

  - hosts: localhost
    connection: local
    gather_facts: false
    tasks:
        - name: create a security group in us-east-1
          ec2_group:
            name: dmz
            description: Dev example ec2 group
            region: us-east-1
            rules:
              - proto: tcp
                from_port: 80
                to_port: 80
                cidr_ip: 0.0.0.0/0
          register: security_group

The above would be deployed if ``runway deploy`` was executed in the ``dev`` environment to ``us-east-1``.
