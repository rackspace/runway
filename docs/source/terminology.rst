.. _blueprints: terminology.html#blueprint
.. _CloudFormation: https://aws.amazon.com/cloudformation/
.. _CloudFormation Parameters: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html
.. _module type: runway_config.html#type
.. _Runway Config File: runway_config.html
.. _stacks: terminology.html#stack
.. _stack definitions: terminology.html#stack-definition
.. _troposphere: https://github.com/cloudtools/troposphere
.. _variables: terminology.html#variable

###########
Terminology
###########


******
Runway
******

.. _term-deploy-env:

Deploy Environment
==================

Deploy environments are used for selecting the options/variables/parameters to be used with each Module_.
They can be defined by the name of a directory (if its not a git repo), git branch, or environment variable (``DEPLOY_ENVIRONMENT``).
Standard deploy environments would be something like prod, dev, and test.


Deployment
==========

A :ref:`deployment<runway-deployment>` contains a list of `modules <#module>`_ and options for
all the modules_ in the deployment_.
A `Runway config file`_ can contain multiple :ref:`deployments<runway-deployment>` and a deployment_ can contain multiple modules_.


Lookup (Runway)
===============

A method for expanding values in the `Runway Config File`_ file when processing a deployment/module.
These are only supported in select areas of the `Runway Config File`_ (see the config docs for more details).


Module
======

A :ref:`module<runway-module>` is a directory containing a single infrastructure-as-code tool configuration of an application, a component, or some infrastructure (eg. a set of `CloudFormation`_ templates).
It is defined in a `deployment`_ by path.
Modules can also contain granular options that only pertain to it based on its `module type`_.


.. _term-param:

Parameters
==========

A mapping of ``key: value`` that is passed to a module.
Through the use of a `Lookup (Runway)`_, the value can be changed per region or deploy environment.
The ``value`` can be any data type but, support for complex data types depends on the `module type`_.


-------------------------------------------------------------------------------


***************
Runway's CFngin
***************


.. _term-blueprint:

Blueprint
=========

A python class that is responsible for creating a CloudFormation template.
Usually this is built using troposphere_.


config
======

A YAML config file that defines the `stack definitions`_ for all of the stacks you want CFNgin to manage.


context
=======

Context is responsible for translating the values passed in via the
command line and specified in the config_ to stacks_.


.. _term-cfngin-env:

environment
===========

A set of variables that can be used inside the config, allowing you to
slightly adjust configs based on which environment you are launching.


.. _term-graph:

graph
=====

A mapping of **object name** to **set/list of dependencies**.

A graph is constructed for each execution of CFNgin from the contents of the
config_ file.

.. rubric:: Example

.. code-block:: json
    {
        "stack1": [],
        "stack2": [
            "stack1"
        ]
    }

- **stack1** depends on nothing.
- **stack2** depends on **stack1**


.. _term-cfngin-hook:

hook
====

These are python functions/methods that are executed before or after the action is taken.


lookup
======

A method for expanding values in the config_ at build time. By default
lookups are used to reference Output values from other stacks_ within the
same namespace_.


namespace
=========

A way to uniquely identify a stack. Used to determine the naming of many
things, such as the S3 bucket where compiled templates are stored, as well
as the prefix for stack names.


.. _term-outputs:

output
======

A CloudFormation Template concept. Stacks can output values, allowing easy
access to those values. Often used to export the unique ID's of resources that
templates create. CFNgin makes it simple to pull outputs from one stack and
then use them as a variable_ in another stack.


persistent graph
================

A graph_ that is persisted between CFNgin executions. It is stored in in the
Stack `S3 bucket <cfngin/config.html#s3-bucket>`_.


provider
========

Provider that supports provisioning rendered blueprints_. By default, an
AWS provider is used.


.. _term-stack:

stack
=====

The resulting stack of resources that is created by CloudFormation when it
executes a template. Each stack managed by CFNgin is defined by a
`stack definition`_ in the config_.


stack definition
================

Defines the stack_ you want to build, usually there are multiple of these in
the config_. It also defines the variables_ to be used when building the stack_.


variable
========

Dynamic variables that are passed into stacks when they are being built.
Variables are defined within the config_.
