#####################
Getting Started Guide
#####################



**************
Basic Concepts
**************

Welcome to Runway!
To get a basic understanding of Runway, we have listed out the key concepts below that you will need to get started with deploying your first module.


Runway Config File
==================

The Runway config file is usually stored at the root of a project repo.
It defines the modules that will be managed by Runway.


Deployment
==========

A :term:`Deployment` contains a list of :term:`Modules <module>` and options for all the :term:`Modules <module>` in the deployment.
A Runway config file can contain multiple :term:`Deployments <Deployment>` and a :term:`Deployment` can contain multiple :term:`Modules <module>`.


Module
======

A :term:`Module` is a directory containing a single infrastructure as code tool configuration of an application, a component, or some infrastructure (eg. a set of CloudFormation templates).
It is defined in a deployment by path.
:term:`Modules <module>` can also contain granular options that only pertain to it.


Deploy Environment
==================

:term:`Deploy Environments <Deploy Environment>` are used for selecting the options/variables/parameters to be used with each :term:`Modules <module>`.
They can be defined by the name of a directory (if its not a git repo), git branch, or environment variable (``DEPLOY_ENVIRONMENT``).
Standard environments would be something like ``prod``, ``dev``, and ``test``.

No matter how the environment is determined, the name is made available to be consumed by your modules as the ``DEPLOY_ENVIRONMENT`` environment variable.



***************************
Deploying Your First Module
***************************

#. Create a directory for our project and change directory into the new directory.

   .. code-block:: sh

    $ mkdir sample-project && cd sample-project

#. Initialize the the new directory as a git repository and checkout branch **ENV-dev**.
   This will give us an environment of **dev**.

   .. code-block:: sh

    $ git init && git checkout -b ENV-dev

#. Install Runway.

   .. tab-set::

    .. tab-item:: poetry (recommended)
      :sync: poetry

      .. code-block:: console

        $ poetry init --quiet
        $ poetry add --group deploy runway

    .. tab-item:: pip (Unix/macOS)
      :sync: pip-unix

      .. code-block:: console

        $ python -m venv .venv
        $ source .venv/bin/activate
        $ pip install runway

    .. tab-item:: pip (Windows)
      :sync: pip-win

      .. code-block:: console

        $ python -m venv .venv
        $ .venv\Scripts\activate
        $ pip install runway

#. Use Runway to generate a sample module using the :ref:`gen-sample <commands:gen-sample>` command.
   This will give us a preformatted CloudFormation :term:`Module` that is ready to be deployed after we change a few variables.
   To read more about the directory structure, see :ref:`repo_structure:Repo Structure`.

   .. code-block:: sh

    $ ./runway gen-sample cfn

   .. tab-set::

    .. tab-item:: poetry (recommended)
      :sync: poetry

      .. code-block:: console

        $ poetry shell
        $ runway gen-sample cfn

    .. tab-item:: pip (Unix/macOS)
      :sync: pip-unix

      .. code-block:: console

        $ runway gen-sample cfn

    .. tab-item:: pip (Windows)
      :sync: pip-win

      .. code-block:: console

        $ runway gen-sample cfn

#. To finish configuring our CloudFormation :term:`Module`, lets open the ``dev-us-east-1.env`` file that was created in ``sampleapp.cfn/``.
   Here is where we will define values for our stacks that will be deployed as part of the **dev** environment in the **us-east-1** region.
   Replace the place holder values in this file with your own information.
   It is important that the ``cfngin_bucket_name`` value is globally unique for this example as it will be used to create a new S3 bucket.

   .. code-block:: yaml
    :caption: dev-us-east-1.env
    :linenos:

    namespace: onica-dev
    customer: onica
    environment: dev
    region: us-east-1
    # The CFNgin bucket is used for CFN template uploads to AWS
    cfngin_bucket_name: cfngin-onica-us-east-1

#. With the :term:`Module` ready to deploy, now we need to create our Runway config file.
   To do this, use the :ref:`commands:new` command to generate a sample file at the root of the project repo.

   .. code-block:: console

    $ runway new

   .. code-block:: yaml
    :caption: runway.yml
    :linenos:

    # See full syntax at https://runway.readthedocs.io
    deployments:
      - modules:
          - nameofmyfirstmodulefolder
          - nameofmysecondmodulefolder
          # - etc...
      regions:
        - us-east-1

#. Now, we need to modify the ``runway.yml`` file that was just created to tell it where the :term:`Module` is located that we want it to deploy and what regions it will be deployed to.
   Each :term:`Module` type has their own configuration options which are described in more detail in the :ref:`index:Module Configuration` section but, for this example we are only concerned with the :ref:`index:CloudFormation & Troposphere`.

   .. code-block:: yaml
    :caption: runway.yml
    :linenos:

    # See full syntax at https://runway.readthedocs.io
    deployments:
      - modules:
          - sampleapp.cfn
      regions:
        - us-east-1

#. Before we deploy, it is always a good idea to know how the :term:`Module` will impact the currently deployed infrastructure in your AWS account.
   This is less of a concern for net-new infrastructure as it is when making modifications.
   But, for this example, lets run the :ref:`commands:plan` command to see what is about to happen.

   .. code-block:: console

    $ runway plan

#. We are finally ready to deploy!
   Use the :ref:`commands:deploy` command to deploy our :term:`Module`.

   .. code-block:: console

    $ runway deploy

We have only scratched the surface with what is possible in this example.
Proceed below to find out how to delete the :term:`Module` we just deployed or, review the pages linked throughout this section to learn more about what we have done to this point before continuing.



**************************
Deleting Your First Module
**************************

From the root of the project directory we created in `Deploying Your First Module`_ we only need to run the :ref:`commands:destroy` command to remove what we have deployed.

.. code-block:: console

  $ runway destroy



*****************************************
Execution Without A TTY (non-interactive)
*****************************************

Runway allows you to set an environment variable to allow execution without a TTY or if STDIN is closed.
This allows users to execute Runway :term:`Deployments <deployment>` in their CI/CD infrastructure as code deployment systems avoiding the ``EOF when reading a line`` error message.
In order to execute Runway without a TTY, set the ``CI`` environment variable before your ``runway [deploy|destroy]`` execution.

.. important::
  Executing Runway in this way will cause Runway to perform updates in your environment without prompt.
  Use with caution.
