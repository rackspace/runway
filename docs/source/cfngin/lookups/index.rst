.. _cfngin-lookups:

#######
Lookups
#######

.. important::
  Runway lookups and CFNgin lookups are not interchangeable.
  While they  do share a similar base class and syntax, they exist in two different registries.
  Runway config files can't use CFNgin lookups just as the CFNgin config cannot use Runway lookups.


Runway's CFNgin provides the ability to dynamically replace values in the config via a concept called lookups.
A lookup is meant to take a value and convert it by calling out to another service or system.

A lookup is denoted in the config with the ``${<lookup type> <lookup input>}`` syntax.

Lookups are only resolved within :ref:`Variables <cfngin-variables>`.
They can be nested in any part of a YAML data structure and within another lookup itself.


.. note::
  If a lookup has a non-string return value, it can be the only lookup within a field.

  e.g. if ``custom`` returns a list, this would raise an exception::

    Variable: ${custom something}, ${output otherStack.Output}

  This is valid::

    Variable: ${custom something}


For example, given the following:

.. code-block:: yaml

  stacks:
    - name: sg
      class_path: some.stack.blueprint.Blueprint
      variables:
        Roles:
          - ${output otherStack.IAMRole}
        Values:
          Env:
            Custom: ${custom ${output otherStack.Output}}
            DBUrl: postgres://${output dbStack.User}@${output dbStack.HostName}

The |Blueprint| would have access to the following resolved variables dictionary:

.. code-block:: python

  {
      "Roles": ["other-stack-iam-role"],
      "Values": {
          "Env": {
              "Custom": "custom-output",
              "DBUrl": "postgres://user@hostname",
          },
      },
  }


----



****************
Built-in Lookups
****************

.. toctree::
  :maxdepth: 1
  :glob:

  **



----


.. _custom lookup:

***********************
Writing A Custom Lookup
***********************

A custom lookup may be registered within the config.
It custom lookup must be in an executable, importable python package or standalone file.
The lookup must be importable using your current ``sys.path``.
This takes into account the :attr:`~cfngin.config.sys_path` defined in the config file as well as any ``paths`` of :class:`~cfngin.package_sources`.

The lookup must be a subclass of :class:`~runway.lookups.handlers.base.LookupHandler` with a ``@classmethod`` of ``handle`` with a similar signature to what is provided in the example below.
The subclass must override the :attr:`~runway.lookups.handlers.base.LookupHandler.TYPE_NAME` class variable with a name that will be used to register the lookup.
There must be only one lookup per file.

The lookup must return a string if being used for a CloudFormation parameter.

If using boto3 in a lookup, use :meth:`context.get_session() <runway.context.CfnginContext.get_session>` instead of creating a new session to ensure the correct credentials are used.

.. important::
  When using a :func:`pydantic.root_validator` or :func:`pydantic.validator` in a lookup ``allow_reuse=True`` must be passed to the decorator.
  This is because of how lookups are loaded/re-loaded when they are registered.
  Failure to do so will result in an error if the lookup is registered more than once.


.. rubric:: Example
.. code-block:: python

  """Example lookup."""

  from __future__ import annotations

  from typing import TYPE_CHECKING, Any, ClassVar

  from runway.cfngin.utils import read_value_from_path
  from runway.lookups.handlers.base import LookupHandler

  if TYPE_CHECKING:
      from runway.cfngin.providers.aws.default import Provider
      from runway.context import CfnginContext


  class MylookupLookup(LookupHandler["CfnginContext"]):
      """My lookup."""

      TYPE_NAME: ClassVar[str] = "my_lookup"
      """Name that the Lookup is registered as."""

      @classmethod
      def handle(
          cls,
          value: str,
          context: CfnginContext,
          *,
          provider: Provider,
          **_kwargs: Any
      ) -> str:
          """Do something.

          Args:
              value: Value to resolve.
              context: The current context object.
              provider: CFNgin AWS provider.

          """
          query, args = cls.parse(read_value_from_path(value))

          # example of using get_session for a boto3 session
          s3_client = context.get_session().client("s3")

          return "something"
