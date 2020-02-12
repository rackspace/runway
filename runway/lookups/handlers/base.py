""".. Base class for lookup handlers.

Lookup Arguments
^^^^^^^^^^^^^^^^

.. _lookup arguments:

Arguments can be passed to Lookups to effect how they function.

To provide arguments to a Lookup, use a double-colon (``::``) after the
query. Each argument is then defined as a **key** and **value** seperated with
equals (``=``) and the arguments theselves are seperated with a comma (``,``).
The arguments can have an optional space after the comma and before the next
key to make them easier to read but this is not required. The value of all
arguments are read as strings.

.. rubric:: Example
.. code-block:: yaml

    ${var my_query::default=true, transform=bool}
    ${env MY_QUERY::default=1,transform=bool}

Each Lookup may have their own, specific arguments that it uses to modify its
functionality or the value it returns. There is also a common set of arguments
that all Lookups accept.

Common Arguments
~~~~~~~~~~~~~~~~

.. _common lookup arguments:

+---------------+-------------------------------------------------------------+
| Argument      | Description                                                 |
+===============+=============================================================+
| ``default``   | If the Lookup is unable to find a value for the provided    |
|               | query, this value will be returned instead of raising a     |
|               | ``ValueError``.                                             |
+---------------+-------------------------------------------------------------+
| ``transform`` | Transform the data returned by a Lookup into a different    |
|               | datatype. Supports ``str`` and ``bool``.                    |
+---------------+-------------------------------------------------------------+

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - environments:
        some_variable: ${var some_value::default=my_value}
        comma_list: ${var my_list::default=undefined, transform=str}

"""
# python2 supported pylint is unable to load this when in a venv
from distutils.util import strtobool  # pylint: disable=E
from typing import (TYPE_CHECKING, Any, Dict,  # noqa: F401 pylint: disable=W
                    Tuple, Union)

from six import string_types

from ...cfngin.util import read_value_from_path

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from ...context import Context  # noqa: F401 pylint: disable=unused-import


class LookupHandler(object):
    """Base class for lookup handlers."""

    @classmethod
    def dependencies(cls, _lookup_data):
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_data may not be (completely) resolved at this time.

        Args:
            lookup_data (VariableValue): Parameter(s) given to this lookup.

        Returns:
            Set

        """
        return set()

    @classmethod
    def handle(cls, value, context, **kwargs):
        # type: (str, 'Context', Any) -> Any
        """Perform the lookup.

        Args:
            value: Parameter(s) given to the lookup.
            context: The current context object.
            provider: Optional provider to use when handling the lookup.

        Returns:
            (Any) Looked-up value.

        """
        raise NotImplementedError

    @classmethod
    def parse(cls, value):
        # type: (str) -> Tuple[str, Dict[str, str]]
        """Parse the value passed to a lookup in a standardized way.

        Args:
            value: The raw value passed to a lookup.

        Returns:
            The lookup query and a dict of arguments

        """
        raw_value = read_value_from_path(value)

        colon_split = raw_value.split('::', 1)

        query = colon_split.pop(0)
        args = cls._parse_args(colon_split[0]) if colon_split else {}

        return query, args

    @classmethod
    def _parse_args(cls, args):
        # type: (str) -> Dict[str, str]
        """Convert a string into an args dict.

        Each arg should be seporated by  ``,``. The key and value should
        be seporated by ``=``. Any leading or following spaces are stripped.

        Args:
            args: A string containing arguments to be parsed. (e.g.
                ``'key1=value1, key2=value2'``)

        Returns:
            Dict of parsed args.

        """
        split_args = args.split(',')
        return {key.strip(): value.strip() for key, value in
                [arg.split('=') for arg in split_args]}

    @classmethod
    def transform(cls, value, to_type='str', **kwargs):
        # type: (str, str, Any) -> Any
        """Transform the result of a lookup into another datatype.

        Args:
            value: What is to be transformed.
            to_type: The type the value will be transformed into.

        Returns:
            The transformed value.

        """
        mapping = {
            'bool': cls._transform_to_bool,
            'str': cls._transform_to_string
        }

        if not to_type:
            return value

        return mapping[to_type](value, **kwargs)  # type: ignore

    @classmethod
    def _transform_to_bool(cls, value, **_):
        # type: (Union[bool, str], Any) -> bool
        """Transform a string into a bool.

        Args:
            value: The value to be transformed into a bool.

        Raises:
            ValueError: The value provided was not a bool or string or
                the string could not be converted to a bool.

        """
        if isinstance(value, bool):
            return value
        if isinstance(value, string_types):
            return bool(strtobool(value))
        raise TypeError('Value must be a string or bool to use transform=bool. '
                        'Got type {}.'.format(type(value)))

    @classmethod
    def _transform_to_string(cls, value, delimiter=None, **_):
        # type: (Any, str, Any) -> str
        """Transform anything into a string.

        If the datatype of ``value`` is a list or similar to a list, ``join()``
        is used to construct the list using a given delimiter or ``,``.

        Args:
            value: The value to be transformed into a string.
            delimited: Used when transforming a list like object into a string
                to join each element together.

        """
        if isinstance(value, (list, set, tuple)):
            return '{}'.format(delimiter or ',').join(value)
        return str(value)
