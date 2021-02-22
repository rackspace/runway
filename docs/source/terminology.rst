.. _blueprints: terminology.html#blueprint
.. _CloudFormation: https://aws.amazon.com/cloudformation/
.. _CloudFormation Parameters: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html
.. _module type: runway_config.html#type
.. _Runway Config File: runway_config.html
.. _troposphere: https://github.com/cloudtools/troposphere

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
The deploy environment is derived from the current directory (if its not a git repo), active git branch, or environment variable (``DEPLOY_ENVIRONMENT``).
Standard deploy environments would be something like prod, dev, and test.

When using a git branch, Runway expects the branch to be prefixed with **ENV-**.
If this is found, Runway knows that it should always use the value that follows the prefix.
If it's the **master** branch, Runway will use the deploy environment name of *common*.
If the branch name does not follow either of these schemas and Runway is being run interactively from the CLI, it will prompt of confirmation of the deploy environment that should be used.

When using a directory, Runway expects the directory's name to be prefixed with **ENV-**.
If this is found, Runway knows that it should always use the value that follows the prefix.


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


context
=======

Context is responsible for translating the values passed in via the
command line and specified in the :class:`~cfngin.config` to :class:`stacks <cfngin.stack>`.


.. _term-graph:

graph
=====

A mapping of **object name** to **set/list of dependencies**.

A graph is constructed for each execution of CFNgin from the contents of the
:class:`~cfngin.config` file.

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


lookup
======

A method for expanding values in the :class:`~cfngin.config` at runtime. By default
lookups are used to reference Output values from other :class:`stacks <cfngin.stack>` within the
same :attr:`~cfngin.config.namespace`.


.. _term-outputs:

output
======

A CloudFormation Template concept.
:class:`Stacks <cfngin.stack>` can output values, allowing easy access to those values.
Often used to export the unique ID's of resources that templates create.

CFNgin makes it simple to pull outputs from one :class:`~cfngin.stack` and then use them in the :attr:`~cfngin.stack.variables` of another :class:`~cfngin.stack`.
