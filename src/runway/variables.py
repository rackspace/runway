"""Runway variables."""
from typing import (Any, Callable,  # noqa: F401 pylint: disable=unused-import
                    Dict, Iterable, Iterator, List, Optional, Type, Union,
                    TYPE_CHECKING, cast)

import logging
import re
from six import string_types

from stacker.exceptions import (InvalidLookupCombination, UnresolvedVariable,  # noqa
                                UnknownLookupType, FailedVariableLookup,
                                FailedLookup, UnresolvedVariableValue,
                                InvalidLookupConcatenation)

from .lookups.registry import LOOKUP_HANDLERS
from .lookups.handlers.base import LookupHandler  # noqa: F401 pylint: disable=unused-import

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from .config import VariablesDefinition  # noqa: F401 pylint: disable=unused-import


LOGGER = logging.getLogger('runway')


class Variable(object):
    """Represents a variable provided to a Runway directive."""

    def __init__(self, name, value):
        # type: (str, Any) -> None
        """Initialize class.

        Args:
            name: Name of the variable (directive/key).
            value: The variable itself.

        """
        LOGGER.debug('Initalized variable "%s".', name)
        self.name = name
        self._raw_value = value
        self._value = VariableValue.parse(value)

    @property
    def resolved(self):
        # type: () -> bool
        """Boolean for whether the Variable has been resolved.

        Variables only need to be resolved if they contain lookups.

        """
        return self._value.resolved

    @property
    def value(self):
        # type: () -> Any
        """Return the current value of the Variable."""
        try:
            return self._value.value
        except UnresolvedVariableValue:
            raise UnresolvedVariable("<unknown>", self)
        except InvalidLookupConcatenation as err:
            raise InvalidLookupCombination(err.lookup, err.lookups, self)

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Recursively resolve any lookups with the Variable.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """
        try:
            self._value.resolve(context, variables=variables, **kwargs)
        except FailedLookup as err:
            raise FailedVariableLookup(self.name, err.lookup, err.error)

    def get(self, key, default=None):
        # type: (Any, Any) -> Any
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self.value, key, default)

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        return 'Variable<{}={}>'.format(self.name, self._raw_value)


class VariableValue(object):
    """Syntax tree base class to parse variable values."""

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved.

        Should be implimented in subclasses.

        """
        raise NotImplementedError

    @property
    def simplified(self):
        # type: () -> Any
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        Should be implimented in subclasses where applicable.

        """
        return self

    @property
    def value(self):
        # type: () -> Any
        """Value of the variable. Can be resolved or unresolved.

        Should be implimented in subclasses.

        """
        raise NotImplementedError

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Resolve the variable value.

        Should be implimented in subclasses.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """

    @classmethod
    def parse(cls, input_object):
        # type: (Any) -> Any
        """Parse complex variable structures using type appropriate subclasses.

        Args:
            input_object: The objected defined as the value of a variable.

        """
        if isinstance(input_object, list):
            return VariableValueList.parse(input_object)
        if isinstance(input_object, dict):
            return VariableValueDict.parse(input_object)
        if not isinstance(input_object, string_types):
            return VariableValueLiteral(input_object)

        tokens = VariableValueConcatenation([
            VariableValueLiteral(t)
            for t in re.split(r'(\$\{|\}|:)', input_object)  # ${ or : or }
        ])

        opener = '${'
        closer = '}'

        while True:
            last_open = None
            next_close = None
            for i, tok in enumerate(tokens):
                if not isinstance(tok, VariableValueLiteral):
                    continue

                if tok.value == opener:
                    last_open = i
                    next_close = None
                if (
                        last_open is not None and
                        tok.value == closer and
                        next_close is None
                ):
                    next_close = i

            if next_close is not None:
                lookup_data = VariableValueConcatenation(
                    tokens[(cast(int, last_open) + len(opener) + 1):next_close]
                )
                lookup = VariableValueLookup(
                    lookup_name=tokens[cast(int, last_open) + 1],
                    lookup_data=lookup_data,
                )
                tokens[last_open:(next_close + 1)] = [lookup]
            else:
                break

        return tokens.simplified

    def __iter__(self):
        # type: () -> Iterable
        """How the object is iterated.

        Should be implimented in subclasses.

        """
        raise NotImplementedError

    def __repr__(self):
        # type: () -> str
        """Return object representation.

        Should be implimented in subclasses.

        """
        raise NotImplementedError


class VariableValueLiteral(VariableValue):
    """The literal value of a variable as provided."""

    def __init__(self, value):
        # type: (Any) -> None
        """Initialize class."""
        self._value = value

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved.

        The ValueLiteral will always appear as resolved because it does
        not "resolve" since it is the literal definition of the value.

        """
        return True

    @property
    def value(self):
        # type: () -> Any
        """Value of the variable."""
        return self._value

    def __iter__(self):
        # type: () -> Iterable[Any]
        """How the object is iterated."""
        yield self

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        return 'Literal<{}>'.format(repr(self._value))


class VariableValueList(VariableValue, list):
    """A list variable value."""

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self:
            accumulator = accumulator and item.resolved
        return accumulator

    @property
    def simplified(self):
        # type: () -> List[VariableValue]
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return [
            item.simplified
            for item in self
        ]

    @property
    def value(self):
        # type: () -> List[Any]
        """Value of the variable. Can be resolved or unresolved."""
        return [
            item.value
            for item in self
        ]

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Resolve the variable value.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """
        for item in self:
            item.resolve(context, variables=variables, **kwargs)

    @classmethod
    def parse(cls, input_object):
        # type: (Any) -> VariableValueList
        """Parse list variable structure.

        Args:
            input_object: The objected defined as the value of a variable.

        """
        acc = [
            VariableValue.parse(obj)
            for obj in input_object
        ]
        return cls(acc)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """How the object is iterated."""
        return list.__iter__(self)

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        return 'List[{}]'.format(', '.join([repr(value)
                                            for value in self]))


class VariableValueDict(VariableValue, dict):
    """A dict variable value."""

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self.values():
            accumulator = accumulator and item.resolved
        return accumulator

    @property
    def simplified(self):
        # type: () -> Dict[str, VariableValue]
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return {
            k: v.simplified
            for k, v in self.items()
        }

    @property
    def value(self):
        # type: () -> Dict[str, Any]
        """Value of the variable. Can be resolved or unresolved."""
        return {
            k: v.value
            for k, v in self.items()
        }

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Resolve the variable value.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """
        for item in self.values():
            item.resolve(context, variables=variables, **kwargs)

    @classmethod
    def parse(cls, input_object):
        # type: (Any) -> VariableValueDict
        """Parse list variable structure.

        Args:
            input_object: The objected defined as the value of a variable.

        """
        acc = {
            k: VariableValue.parse(v)
            for k, v in input_object.items()
        }
        return cls(acc)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """How the object is iterated."""
        return dict.__iter__(self)

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        return 'Dict[{}]'.format(', '.join([
            "{}={}".format(k, repr(v)) for k, v in self.items()
        ]))


class VariableValueConcatenation(VariableValue, list):
    """A concatinated variable value."""

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self:
            accumulator = bool(accumulator and item.resolved)
        return accumulator

    @property
    def simplified(self):
        # type: () -> Union[Type[VariableValue], VariableValueConcatenation, VariableValueLiteral]
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        concat = []  # type: List[Type[VariableValue]]
        for item in self:
            if (
                    isinstance(item, VariableValueLiteral) and
                    item.value == ''
            ):
                pass

            elif (
                    isinstance(item, VariableValueLiteral) and concat and
                    isinstance(concat[-1], VariableValueLiteral)
            ):
                # join the literals together
                concat[-1] = VariableValueLiteral(
                    concat[-1].value + item.value
                )

            elif isinstance(item, VariableValueConcatenation):
                # flatten concatenations
                concat.extend(item.simplified)

            else:
                concat.append(cast(Type[VariableValue], item.simplified))

        if not concat:
            return VariableValueLiteral('')
        if len(concat) == 1:
            return concat[0]
        return VariableValueConcatenation(concat)

    @property
    def value(self):
        # type: () -> Any
        """Value of the variable. Can be resolved or unresolved."""
        if len(self) == 1:
            return self[0].value

        values = []  # type: List[str]
        for value in self:
            resolved_value = value.value
            if not isinstance(resolved_value, string_types):
                raise InvalidLookupConcatenation(value, self)
            values.append(resolved_value)
        return ''.join(values)

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Resolve the variable value.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """
        for value in self:
            value.resolve(context, variables=variables, **kwargs)

    def __iter__(self):
        # type: () -> Iterator[Type[VariableValue]]
        """How the object is iterated."""
        return list.__iter__(self)

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        return 'Concatenation[{}]'.format(
            ', '.join([repr(value) for value in self])
        )


class VariableValueLookup(VariableValue):
    """A lookup variable value."""

    def __init__(self, lookup_name, lookup_data, handler=None):
        # type: (VariableValueLiteral, VariableValue, Type[LookupHandler]) -> None
        """Initialize class.

        Args:
            lookup_name: Name of the invoked lookup
            lookup_data: Data portion of the lookup

        """
        self._resolved = False
        self._value = None

        self.lookup_name = lookup_name

        if isinstance(lookup_data, string_types):
            lookup_data = VariableValueLiteral(lookup_data)
        self.lookup_data = lookup_data

        if handler is None:
            lookup_name_resolved = lookup_name.value
            try:
                handler = cast(Type[LookupHandler], LOOKUP_HANDLERS[lookup_name_resolved])
            except KeyError:
                raise UnknownLookupType(lookup_name_resolved)
        self.handler = handler

    @property
    def resolved(self):
        # type: () -> bool
        """Use to check if the variable value has been resolved."""
        return self._resolved

    @property
    def simplified(self):
        # type: () -> VariableValueLookup
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return VariableValueLookup(
            lookup_name=self.lookup_name,
            lookup_data=self.lookup_data.simplified,
        )

    @property
    def value(self):
        # type: () -> Any
        """Value of the variable. Can be resolved or unresolved."""
        if self._resolved:
            return self._value
        raise UnresolvedVariableValue(self)

    def resolve(self, context, variables=None, **kwargs):
        # type: (Any, 'Optional[VariablesDefinition]', Any) -> None
        """Resolve the variable value.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.

        """
        self.lookup_data.resolve(context, variables=variables, **kwargs)
        try:
            result = self.handler.handle(
                value=self.lookup_data.value,
                context=context,
                variables=variables,
                **kwargs
            )
            self._resolve(result)
        except Exception as err:
            raise FailedLookup(self, err)

    def _resolve(self, value):
        # type: (Any) -> None
        """Set _value and _resolved from the result of resolve()."""
        self._value = value
        self._resolved = True

    def __iter__(self):
        # type: () -> Iterable
        """How the object is iterated."""
        yield self

    def __repr__(self):
        # type: () -> str
        """Return object representation."""
        if self._resolved:
            return 'Lookup<{r} ({t} {d})>'.format(
                r=self._value,
                t=self.lookup_name,
                d=repr(self.lookup_data),
            )
        return 'Lookup<{t} {d}>'.format(
            t=self.lookup_name,
            d=repr(self.lookup_data),
        )

    def __str__(self):
        # type: () -> str
        """Object displayed as a string."""
        return '${{{type} {data}}}'.format(
            type=self.lookup_name.value,
            data=self.lookup_data.value,
        )
