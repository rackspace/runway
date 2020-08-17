""".. Base class for lookup handlers.

.. _lookup arguments:

****************
Lookup Arguments
****************

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

.. _Common Lookup Arguments:

Common Lookup Arguments
=======================

**default (Any)**
    If the Lookup is unable to find a value for the provided query, this
    value will be returned instead of raising an exception.

**get (Optional[str])**
    Can be used on a dictionary type object to retrieve a specific piece of
    data. This is executed after the optional ``load`` step.

**indent (Optional[int])**
    Number of spaces to use per indent level when transforming a dictionary
    type object to a string.

**load (Optional[str])**
    Load the data to be processed by a Lookup using a specific parser. This is
    the first action taking on the data after it has been retrieved from its
    source. The data must be in a format that is supported by the parser
    in order for it to be used.

    **json**
        Loads a JSON seralizable string into a dictionary like object.
    **troposphere**
        Loads the ``properties`` of a subclass of ``troposphere.BaseAWSObject``
        into a dictionary.
    **yaml**
        Loads a YAML seralizable string into a dictionary like object.

**region (Optional[str])**
    AWS region used when creating a ``boto3.Session`` to retrieve data.
    If not provided, the region currently being processed will be used.
    This can be specified to always get data from one region regardless of
    region is being deployed to.

**transform (Optional[str])**
    Transform the data that will be returned by a Lookup into a different
    data type. This is the last action taking on the data before it is
    returned. Supports the following:

    **str**
        Converts any value to a string. The original data type determines the
        end result.

        ``list``, ``set``, and ``tuple`` will become a comma delimited list

        ``dict`` and anything else will become an escaped JSON string.
    **bool**
        Converts a string or boolean value into a boolean.

.. rubric:: Example
.. code-block:: yaml

  deployments:
    - parameters:
        some_variable: ${var some_value::default=my_value}
        comma_list: ${var my_list::default=undefined, transform=str}

"""
import json
import logging
from distutils.util import strtobool  # pylint: disable=E
from typing import (  # noqa: F401 pylint: disable=W
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Tuple,
    Union,
)

import yaml
from six import string_types
from troposphere import BaseAWSObject

from runway.cfngin.util import read_value_from_path
from runway.util import MutableMap

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from ...context import Context  # noqa: F401 pylint: disable=unused-import

LOGGER = logging.getLogger(__name__)


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
    def format_results(
        cls,
        value,  # type: Any
        get=None,  # type: Optional[str]
        load=None,  # type: Optional[str]
        transform=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):
        # type: (...) -> Any
        """Format results to be returned by a lookup.

        Args:
            value (Any): Data collected by the Lookup.
            get (Optional[str]): Nested value to get from a dictionary like
                object.
            load (Optional[str]): Parser to use to parse a formatted string
                before the ``get`` and ``transform`` method.
            transform (Optional[str]): Convert the final value to a different
                data type before returning it.

        Raises:
            TypeError: If ``get`` is provided but the value value is not a
                dictionary like object.

        Runs the following actions in order:

        1. :meth:`~LookupHandler.load` if ``load`` is provided.
        2. :meth:`runway.util.MutableMap.find` or :meth:`dict.get` depending
           on the data type if ``get`` is provided.
        3. :meth:`~LookupHandler.transform` if ``transform`` is provided.

        """
        if load:
            value = cls.load(value, parser=load, **kwargs)
        if get:
            if isinstance(value, MutableMap):
                value = value.find(get)
            elif isinstance(value, dict):
                value = value.get(get)
            else:
                raise TypeError(
                    'value must be dict type to use "get"; got type "{}"'.format(
                        type(value)
                    )
                )
        if transform:
            return cls.transform(value, to_type=transform, **kwargs)
        if isinstance(value, MutableMap):
            LOGGER.debug("returning data from MutableMap")
            return value.data
        return value

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

        colon_split = raw_value.split("::", 1)

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
        split_args = args.split(",")
        return {
            key.strip(): value.strip()
            for key, value in [arg.split("=", 1) for arg in split_args]
        }

    @classmethod
    def load(cls, value, parser=None, **kwargs):
        # type: (str, str, Any) -> Any
        """Load a formatted string or object into a python data type.

        First action taken in :meth:`~LookupHandler.format_results`.
        If a lookup needs to handling loading data to process it before it
        enters :meth:`~LookupHandler.format_results`, is should use
        ``args.pop('load')`` to prevent the data from being loaded twice.

        Args:
            value: What is being loaded.
            parser: Name of the parser to use.

        Returns:
            The loaded value.

        """
        mapping = {
            "json": cls._load_json,
            "troposphere": cls._load_troposphere,
            "yaml": cls._load_yaml,
        }

        if not parser:
            return value

        return mapping[parser](value, **kwargs)

    @classmethod
    def _load_json(cls, value, **_):
        # type: (str, Any) -> MutableMap
        """Load a JSON string into a MutableMap.

        Args:
            value: JSON formatted string.

        Returns:
            MutableMap

        """
        if not isinstance(value, str):
            raise TypeError(
                'value of type "%s" must of type "str" to use the "load=json" argument.'
            )
        result = json.loads(value)
        if isinstance(result, dict):
            return MutableMap(**result)
        return result

    @classmethod
    def _load_troposphere(cls, value, **_):
        # type: (BaseAWSObject, Any) -> MutableMap
        """Load a Troposphere resource into a MutableMap.

        Args:
            Value (troposphere.BaseAWSObject): Troposphere resource to
                contvert to a MutableMap for parsing.

        Returns:
            MutableMap

        """
        if not isinstance(value, BaseAWSObject):
            raise TypeError(
                'value of type "%s" must of type "troposphere.'
                'BaseAWSObject" to use the "load=troposphere" option.'
            )
        if hasattr(value, "properties"):
            return MutableMap(**value.properties)
        raise NotImplementedError(
            '"load=troposphere" only supports BaseAWSObject with a "properties" object.'
        )

    @classmethod
    def _load_yaml(cls, value, **_):
        # type: (str, Any) -> MutableMap
        """Load a YAML string into a MutableMap.

        Args:
            value: YAML formatted string.

        Returns:
            MutableMap

        """
        if not isinstance(value, str):
            raise TypeError(
                'value of type "%s" must of type "str" to use the "load=yaml" argument.'
            )
        result = yaml.safe_load(value)
        if isinstance(result, dict):
            return MutableMap(**result)
        return result

    @classmethod
    def transform(cls, value, to_type="str", **kwargs):
        # type: (str, str, Any) -> Any
        """Transform the result of a lookup into another datatype.

        Last action taken in :meth:`~LookupHandler.format_results`.
        If a lookup needs to handling transforming the data in a way that
        the base class can't support it should overwrite this method of the
        base class to register different transform methods.

        Args:
            value: What is to be transformed.
            to_type: The type the value will be transformed into.

        Returns:
            The transformed value.

        """
        mapping = {"bool": cls._transform_to_bool, "str": cls._transform_to_string}

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
        raise TypeError(
            "Value must be a string or bool to use transform=bool. Got type {}.".format(
                type(value)
            )
        )

    @classmethod
    def _transform_to_string(cls, value, delimiter=None, **kwargs):
        # type: (Any, str, Any) -> str
        """Transform anything into a string.

        If the datatype of ``value`` is a list or similar to a list, ``join()``
        is used to construct the list using a given delimiter or ``,``.

        Args:
            value: The value to be transformed into a string.
            delimiter: Used when transforming a list like object into a string
                to join each element together.

        """
        if isinstance(value, (list, set, tuple)):
            return "{}".format(delimiter or ",").join(value)
        if isinstance(value, MutableMap):
            # convert into a dict with protected attrs removed
            value = value.data
        if isinstance(value, dict):
            # dumped twice for an escaped json dict
            return json.dumps(json.dumps(value, indent=int(kwargs.get("indent", 0))))
        if isinstance(value, bool):
            return json.dumps(str(value))
        return str(value)
