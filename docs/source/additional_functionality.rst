========================
Additional Functionality
========================

whichenv
========
Execute ``runway whichenv`` to output the name of the currently detected environment
(see `Basic Concepts <basic_concepts.html#environments>`_ for an overview of how runway determines the environment name).

gen-sample
==========
Execute ``runway gen-sample`` followed by a module type to create a sample module directory, containing example
files appropriate for the module type:

- ``runway gen-sample cfn``: Creates a sample CloudFormation module in ``sampleapp.cfn``
- ``runway gen-sample sls``: Creates a sample Serverless Framework module in ``sampleapp.sls``
- ``runway gen-sample stacker``: Creates a sample CloudFormation module (with Python templates using Troposphere and awacs) in ``runway-sample-tfstate.cfn``
- ``runway gen-sample tf``: Creates a sample Terraform module in ``sampleapp.tf``

tfenv-runway
============
The ``tfenv-runway`` command shipped with runway provides a way to install Terraform versions by
placing the binary in ``$HOME/.tfenv/versions/X.X.X`` outside of a Runway deployment (e.g.
during a CI build process).

``tfenv-runway install`` can be executed in a directory with a
``.terraform-version`` file to install the version listed in the file.

Alternatively, ``tfenv-runway install VERSION`` can be executed to install a
given version (e.g. ``tfenv-runway install 0.11.6``).

tf-runway
============
The ``tf-runway`` command shipped with runway provides a way to invoke the
version of Terraform specified in your module.

Use it just like the terraform command (e.g. ``tf-runway plan``).

cfn-lint
========
If a ``.cfnlintrc`` file is placed alongside an environment's ``runway.yml``, ``cfn-lint`` will be invoked
automatically during ``runway test`` a.k.a. ``preflight``.

Specify the templates to be included via the `config file. <https://github.com/awslabs/cfn-python-lint#config-file>`_

Runway Plugin Support
=====================
Need to expand runway to wrap other tools? Yes - you can do that with Runway Plugin Support.

Overview
--------
Runway can import Python modules that can perform custom deployments with your
own set of Runway modules. Let's say for example you want to have Runway
execute an Ansible playbook to create an EC2 security group as one of the steps
in the middle of your runway deployment list - this is possible with your own
plugin. The Runway plugin support allows you to mix-and-match natively
supported modules (e.g. CloudFormation, Terraform) with plugins you write
providing additional support for non-native modules. Although written in
Python, these plugins can natively execute non Python binaries.

RunwayModule Class
------------------
Runway provides a Python Class named ``RunwayModule`` that can be imported
into your custom plugin/Python module. This base class will give you the
ability to write your own module that can be added to your runway.yml
deployment list (More info on runway.yml below). There are three required
functions::

- plan - This code block gets called when ``runway taxi`` executes
- deploy - This code block gets called when ``runway takeoff`` executes
- destroy - This code block gets called when ``runway destroy`` executes

All of these functions are required, but are permitted to be empty no-op/pass
statements if applicable.

Context Object
--------------
``self.context`` includes many helpful resources for use in your Python
module. Some notable examples are::

- self.context.env_name - name of the environment
- self.context.env_region - region in which the module is being executed
- self.context.env_vars - OS environment variables provided to the module
- self.path - path to your runway module folder

runway.yml Example
-------------------
After you have written your plugin, you need to add the module ``class_path``
to your module's configuration. Below is an example ``runway.yml`` containing a
single module that looks for an Ansible playbook in a folder at the root of
your Runway environment (i.e. repo) named "security_group.ansible".

Setting ``class_path`` tells runway to import the DeployToAWS Python class,
from a file named Ansible.py in a folder named "local_runway_extensions"
(Standard Python import conventions apply). Runway will execute the ``deploy``
function in your class when you perform a ``runway deploy`` (AKA takeoff).

::

    deployments:
      - modules:
          - path: security_group.ansible
            class_path: local_runway_extensions.Ansible.DeployToAWS
        regions:
          - us-east-1


Below is the ``Ansible.py`` module referenced above that wraps the
``ansible-playbook`` command. It will be responsible for deploying an EC2 Security Group from the playbook
with a naming convention of ``<env>-<region>.yaml`` within a fictional
``security_group.ansible`` runway module folder. In this example, the
``ansible-playbook`` binary would already have been installed prior to a runway
deploy, but this example does check to see if it is installed before execution
and logs an error if not. The Runway plugin will only execute
the ansible-playbook against a ``yaml`` file associated with the environment and set for the Runway
execution and region defined in the ``runway.yml``.

Using the above ``runway.yml`` and the plugin/playbook below saved to the Runway
module folder you will only have a deployment occur in the ``dev`` environment
in ``us-east-1``.  If you decide to perform a runway deployment in the ``prod``
environment, or in a different region, the ansible-playbook deployment will be
skipped. This matches the behavior of the Runway's native modules.

::

    """Ansible Plugin example for Runway."""

    import logging
    import subprocess
    import sys
    import os

    from runway.module import RunwayModule
    from runway.util import which

    LOGGER = logging.getLogger('runway')


    def check_for_playbook(playbook_path):
        """Determine if environment/region playbook exists."""
        if os.path.isfile(playbook_path):
            LOGGER.info("Processing playbook: %s", playbook_path)
            return {'skipped_configs': False}
        else:
            LOGGER.error("No playbook for this environment/region found -- "
                         "looking for %s", playbook_path)
            return {'skipped_configs': True}


    class DeployToAWS(RunwayModule):
        """Ansible Runway Module."""

        def plan(self):
            """Skip plan"""
            LOGGER.info('plan not currently supported for Ansible')
            pass

        def deploy(self):
            """Run ansible-playbook."""
            if not which('ansible-playbook'):
                LOGGER.error('"ansible-playbook" not found in path or is not '
                             'executable; please ensure it is installed'
                             'correctly.')
                sys.exit(1)
            playbook_path = (self.path + "-" + self.context.env_name + self.context.env_region)
            response = check_for_playbook(playbook_path)
            if response['skipped_configs']:
                return response
            else:
                subprocess.check_output(
                    ['ansible-playbook', playbook_path])
                return response

        def destroy(self):
            """Skip destroy."""
            LOGGER.info('Destroy not currently supported for Ansible')
            pass



And below is the example Ansible playbook itself, saved as
``dev-us-east-1.yaml`` in the security_group.ansible folder:

::

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


The above would be deployed if ``runway deploy`` was executed in the ``dev``
environment to ``us-east-1``.
