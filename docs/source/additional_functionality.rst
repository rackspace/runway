Addtional Functionality
=======================

whichenv
^^^^^^^^
Execute ``runway whichenv`` to output the name of the currently detected environment
(see `Basic Concepts <basic_concepts.html#environments>`_ for an overview of how runway determines the environment name).

gen-sample
^^^^^^^^^^
Execute ``runway gen-sample`` followed by a module type to create a sample module directory, containing example
files appropriate for the module type:

- ``runway gen-sample cfn``: Creates a sample CloudFormation module in ``sampleapp.cfn``
- ``runway gen-sample sls``: Creates a sample Serverless Framework module in ``sampleapp.sls``
- ``runway gen-sample stacker``: Creates a sample CloudFormation module (with Python templates using Troposphere and awacs) in ``runway-sample-tfstate.cfn``
- ``runway gen-sample tf``: Creates a sample Terraform module in ``sampleapp.tf``

cfn-lint
^^^^^^^^^^
If a ``.cfnlintrc`` file is placed alongside an environment's ``runway.yml``, cfn-lint will be invoked
automatically during runway test aka preflight.

Specify the templates to be included via the `config file. <https://github.com/awslabs/cfn-python-lint#config-file>`_

Runway Plugin Support
^^^^^^^^^^^^^^^^^^^^^
Need to expand runway to wrap other tools? Yes - you can do that with Runway Plugin Support.

**Overview**

Runway can import Python modules that can perform custom deployments with your own set of Runway modules. Let's say for example you want to have runway execute an Ansible playbook to create an EC2 security group as one of the steps in the middle of your runway deployment list. This is possible with your own plugin. The Runway plugin support allows you to mix-and-match natively supported modules (Cloudformation / Terreform / Serverless) with plugins you write providing additional support for non-native modules. Although written in Python, these plugins can natively execute non Python binaries.

**RunwayModule Class**

Runway provides a Python Class named ``RunwayModule`` that can be imported into your custom plugin/Python module. This base class will give you the ability to write your own module that can be added to your runway.yaml deployment list (More info on runway.yaml below). There are three required functions you need to include in your Python class for your module to be executed in all potential runway execution scenarios, they are:

*Required functions*

- plan - This code block gets called when ``runway taxi`` executes
- deploy - This code block gets called when ``runway takeoff`` executes
- destroy - This code block gets called when ``runway destroy`` executes

If you don't have any actions you want taken for a specific function, you must still include it, however it may be an empty no-op/pass statement. Each of the above function must pass in the ``self`` object to allow for context to be used in the function. self.context includes many helpful resources for use in your Python module. Some notable examples are:

- self.context.env_name - this provides the name of the environment
- self.context.env_region - this provides the region context the module is being executed in
- self.context.env_vars - this provides the environment variables
- self.path - the path to your runway module folder, set in runway.yaml under ``path``.

*runway.yaml example*

After you have written your Runway Plugin, you need to add the module ``class_path`` in your runway deployment list. Below is an example runway.yaml containing a single runway module that looks for an Ansible playbook in a folder/Runway module at the root of your repo named "security_group.ansible". Setting ``class_path`` tells runway to import the DeployToAWS Python Class, from a file named Ansible.py in a folder named "local_runway_extensions" (Standard Python import conventions apply). Runway will execute the ``deploy`` function in your class when you perform a ``runway deploy`` or ``runway takeoff``.

::

    deployments:
      - modules:
          - path: security_group.ansible
            class_path: local_runway_extensions.Ansible.DeployToAWS
        regions:
          - us-east-1


The below is an example Runway Plugin that wraps the ``anisble-playbook`` command to deploy a EC2 Security Group from a playbook yaml under the naming convention of ``<env>-<region>.yaml`` within a fictional ``security_group.ansible`` runway module folder. In this example, the ``anisble-playbook`` binary would already have been installed prior to a runway deploy, but this example does check to see if it is installed before execution and logs an error if that is the case. The Runway plugin also will only execute the ansible-playbook against a yaml file for the environment set for thr runway execution and region defined in the runway.yaml. 

Using the above runway.yaml, the below plugin and below playbook saved in the runway module folder, you will only have a deployment occur in the ``dev`` environment in ``us-east-1``.  If you decide to perform a runway deployment in a the ``prod`` environment or in a different region, the anisble-playbook deployment will be skipped. This matches the built in behavior of the native modules runway includes. 

::

    """Anisble Plugin example for Runway."""

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
        """Anisble Runway Module."""

        def plan(self):
            """Skip plan"""
            LOGGER.info('plan not currently supported for Anisble')
            pass

        def deploy(self):
            """Run anisble-playbook."""
            if not which('anisble-playbook'):
                LOGGER.error('"anisble-playbook" not found in path or is not '
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
            LOGGER.info('Destroy not currently supported for Anisble')
            pass



And below is the example Ansible playbook itself, saved as ``dev-us-east-1.yaml`` in the security_group.anisble folder:

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


The above would be deployed if ``runway deploy`` was executed in the ``dev`` environment to us-east-1.
