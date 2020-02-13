.. _CloudFormation: https://aws.amazon.com/cloudformation/

Getting Started Guide
=====================


Basic Concepts
^^^^^^^^^^^^^^

Welcome to Runway! To get a basic understanding of Runway, we have listed out
the key concepts below that you will need to get started with deploying your
first `module`_.


Runway Config File
~~~~~~~~~~~~~~~~~~

The :ref:`Runway config file<runway-config>` is usually stored at the root of
a project repo. It defines the `modules <module>`_ that will be managed by
Runway.


Deployment
~~~~~~~~~~

A :ref:`deployment<runway-deployment>` contains a list of `modules <module>`_
and options for all the `modules <module>`_ in the
:ref:`deployment<runway-deployment>`. A `Runway config file`_ can contain
multiple :ref:`deployments<runway-deployment>` and a
:ref:`deployment<runway-deployment>` can contain multiple `modules <module>`_.


Module
~~~~~~

A :ref:`module<runway-module>` is a directory containing a single
infrastructure-as-code tool configuration of an application, a component, or
some infrastructure (eg. a set of `CloudFormation`_ templates). It is
defined in a `deployment`_ by path. Modules can also contain granular options
that only pertain to it.


Environment
~~~~~~~~~~~

Environments are used for selecting the options/variables/parameters to be
used with each `modules <module>`_. They can be defined by the name of a
directory (if its not a git repo), git branch, or environment variable
(``DEPLOY_ENVIRONMENT``). Standard environments would be something like prod,
dev, and test.

No matter how the environment is determined, the name is made available
to be consumed by your `modules <module>`_ as the ``DEPLOY_ENVIRONMENT``
environment variable.


Deploying Your First Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Create a directory for our project and change directory into the new
   directory.

   .. code-block:: shell

       # macOS example
       $ mkdir sample-project
       $ cd sample-project

#. Initialize the the new directory as a git repo and checkout branch
   **ENV-dev**. This will give us an environment of **dev**.

   .. code-block:: shell

       # macOS example
       $ git init
       $ git checkout -b ENV-dev

#. Download Runway using :ref:`curl<install-curl>`. Be sure to use the endpoint
   that corresponds to your operating system. Then, change the downloaded
   file's permissions to allow execution.

   .. code-block:: shell

       # macOS example
       $ curl -L https://oni.ca/runway/latest/osx -o runway
       $ chmod +x runway

#. Use Runway to generate a sample :ref:`module<runway-module>` using the
   :ref:`gen-sample<command-gen-sample>` command. This will give us a
   preformatted :ref:`module<runway-module>` that is ready to be deployed after
   we change a few variables. To read more about the directory structure,
   see :ref:`repo-structure`.

   .. code-block:: shell

       $ ./runway gen-sample cfn

#. To finish configuring our `CloudFormation`_ :ref:`module<runway-module>`
   , lets open the ``dev-us-east-1.env`` file that was created in
   ``sampleapp.cfn/``. Here is where we will define values for our stacks that
   will be deployed as part of the **dev** environment in the **us-east-1**
   region. Replace the place holder values in this file with your own
   information. It is important that the ``cfngin_bucket_name`` value is
   globally unique for this example as it will be used to create a new S3
   bucket.

   .. code-block:: yaml

       namespace: onica-dev
       customer: onica
       environment: dev
       region: us-east-1
       # The CFNgin bucket is used for CFN template uploads to AWS
       cfngin_bucket_name: cfngin-onica-us-east-1

#. With the :ref:`module<runway-module>` ready to deploy, now we need to create
   our :ref:`Runway config file<runway-config>`. Do to this, use the
   :ref:`init<command-init>` command to generate a sample file at the root of
   the project repo.

   .. code-block:: shell

       $ ./runway init

   **runway.yml contents**

   .. code-block:: yaml

       ---
       # See full syntax at https://docs.onica.com/projects/runway/en/latest/
       deployments:
         - modules:
             - nameofmyfirstmodulefolder
             - nameofmysecondmodulefolder
             # - etc...
         regions:
           - us-east-1

#. Now, we need to modify the ``runway.yml`` file that was just created to
   tell it where the :ref:`module<runway-module>` is located that we want it to
   deploy and what regions it will be deployed to. Each
   :ref:`module<runway-module>` type has their own configuration options which
   are described in more detail in the
   :ref:`Module Configurations<module-configurations>` section but, for this
   example we are only concerned with the
   :ref:`CloudFormation module configuration<mod-cfn>`.

   The end result should like this:

   .. code-block:: yaml

       ---
       # See full syntax at https://docs.onica.com/projects/runway/en/latest/
       deployments:
         - modules:
             - sampleapp.cfn
         regions:
           - us-east-1

#. Before we deploy, it is always a good idea to know how the
   :ref:`module<runway-module>` will impact the currently deployed
   infrastructure in your AWS account. This is less of a concern for net-new
   infrastructure as it is when making modifications. But, for this example,
   lets run the :ref:`plan<command-plan>` command to see what is about to
   happen.

      .. code-block:: shell

       $ ./runway plan

#. We are finally ready to deploy! Use the :ref:`deploy<command-deploy>`
   command to deploy our :ref:`module<runway-module>`.

   .. code-block:: shell

       $ ./runway deploy

We have only scratched the surface with what is possible in this example.
Proceed below to find out how to delete the :ref:`module<runway-module>` we
just deployed or, review the pages linked throughout this section to learn more
about what we have done to this point before continuing.


Deleting Your First Module
^^^^^^^^^^^^^^^^^^^^^^^^^^

From the root of the project directory we created in
`Deploying Your First Module`_ we only need to run the
:ref:`destroy<command-destroy>` command to remove what we have deployed.

.. code-block:: shell

    $ ./runway destroy


.. _non-interactive-mode:

Execution Without A TTY (non-interactive)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Runway allows you to set an environment variable to allow execution without a
TTY or if STDIN is closed. This allows users to execute Runway
:ref:`deployments<runway-deployment>` in their CI/CD infrastructure as code
deployment systems avoiding the ``EOF when reading a line`` error message.
In order to execute runway without a TTY, set the ``CI`` environment variable
before your ``runway [deploy|destroy]`` execution.

.. important:: Executing Runway in this way will cause Runway to perform updates
               in your environment without prompt.  Use with caution.
