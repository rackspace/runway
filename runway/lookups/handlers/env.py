"""Retrieve a value from an environment variable.

The value is retrieved from a copy of the current environment variables
that is saved to the context object. These environment variables are
manipulated at runtime by Runway to fill in additional values such as
``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the current execution.

.. note:: ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` can only be resolved
          during the processing of a module. To ensure no error occurs
          when trying to resolve one of these in a :ref:`Deployment
          <runway-deployment>` definition, provide a default value.

If the Lookup is unable to find an environment variable matching the
provided query, the default value is returned or a ``ValueError`` is raised
if a default value was not provided.

.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments` but, the folling have
limited or no effect:

- region


.. rubric:: Example
.. code-block:: yaml

  deployment:
    - modules:
        - path: sampleapp.cfn
          parameters:
            creator: ${env USER}
      env_vars:
        ENVIRONMENT: ${env DEPLOY_ENVIRONMENT::default=default}

"""
# pylint: disable=arguments-differ
from typing import Any, TYPE_CHECKING  # pylint: disable=unused-import

from .base import LookupHandler

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from ...context import Context  # noqa: F401 pylint: disable=unused-import

TYPE_NAME = "env"


class EnvLookup(LookupHandler):
    """Environment variable Lookup."""

    @classmethod
    def handle(cls, value, context, **_):
        # type: (str, 'Context', Any) -> Any
        """Retrieve an environment variable.

        The value is retrieved from a copy of the current environment variables
        that is saved to the context object. These environment variables
        are manipulated at runtime by Runway to fill in additional values
        such as ``DEPLOY_ENVIRONMENT`` and ``AWS_REGION`` to match the
        current execution.

        Args:
            value: The value passed to the Lookup.
            context: The current context object.

        Raises:
            ValueError: Unable to find a value for the provided query and
                a default value was not provided.

        """
        query, args = cls.parse(value)

        result = context.env_vars.get(query, args.pop('default', ''))

        if result != '':  # allows for False bool and NoneType results
            return cls.format_results(result, **args)

        raise ValueError('"{}" does not exist in the environment'.format(value))
