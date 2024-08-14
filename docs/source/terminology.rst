###########
Terminology
###########

.. glossary::
  Blueprint
    A python class that is responsible for creating a :link:`CloudFormation` template using :link:`troposphere`.
    :term:`Blueprints <Blueprint>` are deploying using :term:`CFNgin`.

  CFNgin
    Runway's CloudFormation engine used to deploy :link:`CloudFormation` Templates (JSON or YAML) and :term:`Blueprints <Blueprint>` written using :link:`troposphere`.

  Deploy Environment
    :term:`Deploy Environments <Deploy Environment>` are used for selecting the options/variables/parameters to be used with each :term:`Module`.
    The :term:`Deploy Environment` is derived from the current directory (if its not a git repo), active git branch, or environment variable (``DEPLOY_ENVIRONMENT``).
    Standard :term:`Deploy Environments <Deploy Environment>` would be something like prod, dev, and test.

    When using a git branch, Runway expects the branch to be prefixed with **ENV-**.
    If this is found, Runway knows that it should always use the value that follows the prefix.
    If it's the **master** branch, Runway will use the :term:`Deploy Environment` name of *common*.
    If the branch name does not follow either of these schemas and Runway is being run interactively from the CLI, it will prompt of confirmation of the :term:`Deploy Environment` that should be used.

    When using a directory, Runway expects the directory's name to be prefixed with **ENV-**.
    If this is found, Runway knows that it should always use the value that follows the prefix.

  Deployment
    A :ref:`Deployment <runway-deployment>` contains a list of :term:`Modules <Module>` and options for all the :term:`Modules <Module>` in the :term:`Deployment`.
    A :ref:`runway-config` can contain multiple :ref:`deployments <runway-deployment>` and a :term:`Deployment` can contain multiple :term:`Modules <Module>`.

  Lookup
    In the context of Runway, a :term:`Lookup` is a method for expanding values in the :ref:`runway-config` file when processing a :term:`Deployment`/:term:`Module`.
    These are only supported in select areas of the :ref:`runway-config` (see the config docs for more details).

    In the context of :term:`CFNgin`, a :term:`Lookup` is method for expanding values in the :class:`~cfngin.config` at runtime.

  Module
    A :ref:`Module <runway-module>` is a directory containing a single Infrastructure-as-Code tool configuration of an application, a component, or some infrastructure (e.g. a set of :link:`CloudFormation` Templates).
    It is defined in a :term:`Deployment` by path.
    :term:`Modules <Module>` can also contain granular options that only pertain to it based on its :attr:`module.type`.

  Output
    A :link:`CloudFormation` Template concept.
    :class:`Stacks <cfngin.stack>` can output values allowing easy access to those values.
    Often used to export the unique ID's of resources that Templates create.

    :term:`CFNgin` makes it easy to pull :term:`Outputs <Output>` from one :class:`~cfngin.stack` and then use them in the :attr:`~cfngin.stack.variables` of another :class:`~cfngin.stack`.

  Parameters
    A mapping of ``key: value`` that is passed to a :term:`Module`.
    Through the use of a :term:`Lookup`, the value can be changed per region or :term:`Deploy Environment`.
    The ``value`` can be any data type but, support for complex data types depends on the :attr:`module.type`.

  graph
    A mapping of **object name** to **set/list of dependencies**.

    A graph is constructed for each execution of :term:`CFNgin` from the contents of a :class:`~cfngin.config` file.

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
