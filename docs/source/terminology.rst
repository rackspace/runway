.. _blueprints: terminology.html#blueprint
.. _CloudFormation Parameters: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html
.. _stacks: terminology.html#stack
.. _stack definitions: terminology.html#stack-definition
.. _troposphere: https://github.com/cloudtools/troposphere
.. _variables: terminology.html#variable

===========
Terminology
===========

CFngin
======


Blueprint
---------

A python class that is responsible for creating a CloudFormation template.
Usually this is built using troposphere_.


config
------

A YAML config file that defines the `stack definitions`_ for all of the stacks you want CFNgin to manage.


context
-------

Context is responsible for translating the values passed in via the
command line and specified in the config_ to stacks_.


environment
-----------

A set of variables that can be used inside the config, allowing you to
slightly adjust configs based on which environment you are launching.


graph
-----

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


hook
----

These are python functions/methods that are executed before or after the action is taken.


lookup
------

A method for expanding values in the config_ at build time. By default
lookups are used to reference Output values from other stacks_ within the
same namespace_.


namespace
---------

A way to uniquely identify a stack. Used to determine the naming of many
things, such as the S3 bucket where compiled templates are stored, as well
as the prefix for stack names.


output
------

A CloudFormation Template concept. Stacks can output values, allowing easy
access to those values. Often used to export the unique ID's of resources that
templates create. CFNgin makes it simple to pull outputs from one stack and
then use them as a variable_ in another stack.


persistent graph
----------------

A graph_ that is persisted between CFNgin executions. It is stored in in the
Stack `S3 bucket <cfngin/config.html#s3-bucket>`_.


provider
--------

Provider that supports provisioning rendered blueprints_. By default, an
AWS provider is used.


stack
-----

The resulting stack of resources that is created by CloudFormation when it
executes a template. Each stack managed by CFNgin is defined by a
`stack definition`_ in the config_.


stack definition
----------------

Defines the stack_ you want to build, usually there are multiple of these in
the config_. It also defines the variables_ to be used when building the stack_.


variable
--------

Dynamic variables that are passed into stacks when they are being built.
Variables are defined within the config_.
