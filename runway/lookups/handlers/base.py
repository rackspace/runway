"""Base class for lookup handlers."""
from __future__ import annotations

import json
import logging
from distutils.util import strtobool
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Set, Tuple, Union, cast

import yaml
from troposphere import BaseAWSObject
from typing_extensions import Literal

from ...cfngin.utils import read_value_from_path
from ...utils import MutableMap

if TYPE_CHECKING:
    from ...cfngin.providers.aws.default import Provider
    from ...context import CfnginContext, RunwayContext
    from ...variables import VariableValue

LOGGER = logging.getLogger(__name__)

TransformToTypeLiteral = Literal["bool", "str"]


class LookupHandler:
    """Base class for lookup handlers."""

    @classmethod
    def dependencies(cls, __lookup_query: VariableValue) -> Set[str]:
        """Calculate any dependencies required to perform this lookup.

        Note that lookup_query may not be (completely) resolved at this time.

        """
        return set()

    @classmethod
    def format_results(
        cls,
        value: Any,
        get: Optional[str] = None,
        load: Optional[str] = None,
        transform: Optional[TransformToTypeLiteral] = None,
        **kwargs: Any,
    ) -> Any:
        """Format results to be returned by a lookup.

        Args:
            value: Data collected by the Lookup.
            get: Nested value to get from a dictionary like object.
            load: Parser to use to parse a formatted string before the ``get``
                and ``transform`` method.
            transform: Convert the final value to a different data type before
                returning it.

        Raises:
            TypeError: If ``get`` is provided but the value value is not a
                dictionary like object.

        Runs the following actions in order:

        1. :meth:`load` if ``load`` is provided.
        2. :meth:`runway.util.MutableMap.find` or :meth:`dict.get` depending
           on the data type if ``get`` is provided.
        3. Convert null value string to ``NoneType`` object. This includes string
           values of "None" and "null". This conversion is case insensitive.
        4. :meth:`transform` if ``transform`` is provided.

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
                    f'value must be dict type to use "get"; got type "{type(value)}"'
                )
        if (
            isinstance(value, str)
            and value.lower() in ["none", "null"]
            and transform != "str"  # retain string "as is" if should be str
        ):
            value = None
        if transform:
            return cls.transform(value, to_type=transform, **kwargs)
        if isinstance(value, MutableMap):
            LOGGER.debug("returning data from MutableMap")
            return value.data
        return value

    @classmethod
    def handle(
        cls,
        __value: str,
        context: Union[CfnginContext, RunwayContext],
        *__args: Any,
        provider: Optional[Provider] = None,
        **__kwargs: Any,
    ) -> Any:
        """Perform the lookup.

        Args:
            __value: Parameter(s) given to the lookup.
            context: The current context object.
            provider: CFNgin AWS provider.

        """
        raise NotImplementedError

    @classmethod
    def parse(cls, value: str) -> Tuple[str, Dict[str, str]]:
        """Parse the value passed to a lookup in a standardized way.

        Args:
            value: The raw value passed to a lookup.

        Returns:
            The lookup query and a dict of arguments

        """
        raw_value = read_value_from_path(value)

        colon_split = raw_value.split("::", 1)

        query = colon_split.pop(0)
        args: Dict[str, str] = cls._parse_args(colon_split[0]) if colon_split else {}

        return query, args

    @classmethod
    def _parse_args(cls, args: str) -> Dict[str, str]:
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
    def load(cls, value: Any, parser: Optional[str] = None, **kwargs: Any) -> Any:
        """Load a formatted string or object into a python data type.

        First action taken in :meth:`format_results`.
        If a lookup needs to handling loading data to process it before it
        enters :meth:`format_results`, is should use
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
    def _load_json(cls, value: Any, **_: Any) -> MutableMap:
        """Load a JSON string into a MutableMap.

        Args:
            value: JSON formatted string.

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
    def _load_troposphere(cls, value: Any, **_: Any) -> MutableMap:
        """Load a Troposphere resource into a MutableMap.

        Args:
            value: Troposphere resource to contvert to a MutableMap for parsing.

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
    def _load_yaml(cls, value: Any, **_: Any) -> MutableMap:
        """Load a YAML string into a MutableMap.

        Args:
            value: YAML formatted string.

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
    def transform(
        cls,
        value: Any,
        *,
        to_type: Optional[TransformToTypeLiteral] = "str",
        **kwargs: Any,
    ) -> Any:
        """Transform the result of a lookup into another datatype.

        Last action taken in :meth:`format_results`.
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
    def _transform_to_bool(cls, value: Any, **_: Any) -> bool:
        """Transform a string into a bool.

        Args:
            value: The value to be transformed into a bool.

        Raises:
            ValueError: The value provided was not a bool or string or
                the string could not be converted to a bool.

        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return bool(strtobool(value))
        raise TypeError(
            f"Value must be a string or bool to use transform=bool. Got type {type(value)}."
        )

    @classmethod
    def _transform_to_string(
        cls, value: Any, *, delimiter: str = ",", indent: int = 0, **_: Any
    ) -> str:
        """Transform anything into a string.

        If the datatype of ``value`` is a list or similar to a list, ``join()``
        is used to construct the list using a given delimiter or ``,``.

        Args:
            value: The value to be transformed into a string.
            delimiter: Used when transforming a list like object into a string
                to join each element together.
            indent: Number of spaces to use when indenting JSON output.

        """
        if isinstance(value, (list, set, tuple)):
            return f"{delimiter}".join(cast(Sequence[str], value))
        if isinstance(value, MutableMap):
            # convert into a dict with protected attrs removed
            value = value.data
        if isinstance(value, dict):
            # dumped twice for an escaped json dict
            return json.dumps(
                json.dumps(cast(Dict[str, Any], value), indent=int(indent))
            )
        if isinstance(value, bool):
            return json.dumps(str(value))
        return str(value)
