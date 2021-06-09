"""Runway variables."""
from __future__ import annotations

import logging
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    MutableSequence,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import Literal

from .cfngin.lookups.registry import CFNGIN_LOOKUP_HANDLERS
from .exceptions import (
    FailedLookup,
    FailedVariableLookup,
    InvalidLookupConcatenation,
    UnknownLookupType,
    UnresolvedVariable,
    UnresolvedVariableValue,
)
from .lookups.handlers.base import LookupHandler
from .lookups.registry import RUNWAY_LOOKUP_HANDLERS

if TYPE_CHECKING:
    from .cfngin.providers.aws.default import Provider
    from .config.components.runway import RunwayVariablesDefinition
    from .context import CfnginContext, RunwayContext

LOGGER = logging.getLogger(__name__)

_LiteralValue = TypeVar("_LiteralValue", int, str)
VariableTypeLiteralTypeDef = Literal["cfngin", "runway"]


class Variable:
    """Represents a variable provided to a Runway directive."""

    name: str

    def __init__(
        self,
        name: str,
        value: Any,
        variable_type: VariableTypeLiteralTypeDef = "cfngin",
    ) -> None:
        """Initialize class.

        Args:
            name: Name of the variable (directive/key).
            value: The variable itself.
            variable_type: Type of variable (cfngin|runway).

        """
        self.name = name
        self._raw_value = value
        self._value = VariableValue.parse_obj(value, variable_type)
        self.variable_type = variable_type

    @property
    def dependencies(self) -> Set[str]:
        """Stack names that this variable depends on.

        Returns:
            Set[str]: Stack names that this variable depends on.

        """
        return self._value.dependencies

    @property
    def resolved(self) -> bool:
        """Boolean for whether the Variable has been resolved.

        Variables only need to be resolved if they contain lookups.

        """
        return self._value.resolved

    @property
    def value(self) -> Any:
        """Return the current value of the Variable.

        Raises:
            UnresolvedVariable: Value accessed before it have been resolved.

        """
        try:
            return self._value.value
        except UnresolvedVariableValue:
            raise UnresolvedVariable(self) from None

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        Raises:
            FailedVariableLookup

        """
        try:
            self._value.resolve(
                context, provider=provider, variables=variables, **kwargs
            )
        except FailedLookup as err:
            raise FailedVariableLookup(self, err) from err.cause

    def get(self, key: str, default: Any = None) -> Any:
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self.value, key, default)

    def __repr__(self) -> str:
        """Return object representation."""
        return f"Variable[{self.name}={self._raw_value}]"


def resolve_variables(
    variables: List[Variable],
    context: Union[CfnginContext, RunwayContext],
    provider: Optional[Provider] = None,
) -> None:
    """Given a list of variables, resolve all of them.

    Args:
        variables: List of variables.
        context: CFNgin context.
        provider: Subclass of the base provider.

    """
    for variable in variables:
        variable.resolve(context=context, provider=provider)


_VariableValue = TypeVar("_VariableValue", bound="VariableValue")


class VariableValue:
    """Syntax tree base class to parse variable values."""

    _resolved: bool = False
    _data: Any
    variable_type: VariableTypeLiteralTypeDef

    @property
    def dependencies(self) -> Set[Any]:
        """Stack names that this variable depends on."""
        return set()

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved.

        Raises:
            NotImplementedError: Should be defined in a subclass.

        """
        raise NotImplementedError

    @property
    def simplified(self) -> Any:
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        Should be implimented in subclasses where applicable.

        """
        return self

    @property
    def value(self) -> Any:
        """Value of the variable. Can be resolved or unresolved.

        Raises:
            NotImplementedError: Should be defined in a subclass.

        """
        raise NotImplementedError

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        """

    def _resolve(self, value: Any) -> None:
        """Set _value and _resolved from the result of resolve().

        Args:
            value: Resolved value of the variable.

        """
        self._data = value
        self._resolved = True

    @overload
    @classmethod
    def parse_obj(
        cls, obj: Dict[str, Any], variable_type: VariableTypeLiteralTypeDef = ...
    ) -> VariableValue:
        ...

    @overload
    @classmethod
    def parse_obj(
        cls, obj: List[Any], variable_type: VariableTypeLiteralTypeDef = ...
    ) -> VariableValueList:
        ...

    @overload
    @classmethod
    def parse_obj(
        cls, obj: int, variable_type: VariableTypeLiteralTypeDef = ...
    ) -> VariableValueLiteral[int]:
        ...

    @overload
    @classmethod
    def parse_obj(
        cls, obj: str, variable_type: VariableTypeLiteralTypeDef = ...
    ) -> VariableValueConcatenation[
        Union[VariableValueLiteral[str], VariableValueLookup]
    ]:
        ...

    @classmethod
    def parse_obj(
        cls, obj: Any, variable_type: VariableTypeLiteralTypeDef = "cfngin"
    ) -> VariableValue:
        """Parse complex variable structures using type appropriate subclasses.

        Args:
            obj: The objected defined as the value of a variable.
            variable_type: Type of variable (cfngin|runway).

        """
        if isinstance(obj, dict):
            return VariableValueDict(obj, variable_type=variable_type)  # type: ignore
        if isinstance(obj, list):
            return VariableValueList(obj, variable_type=variable_type)  # type: ignore
        if not isinstance(obj, str):
            return VariableValueLiteral(obj, variable_type=variable_type)  # type: ignore

        tokens: VariableValueConcatenation[
            Union[VariableValueLiteral[str], VariableValueLookup]
        ] = VariableValueConcatenation(
            # pyright 1.1.138 is having issues properly inferring the type from comprehension
            [  # type: ignore
                VariableValueLiteral(cast(str, t), variable_type=variable_type)
                for t in re.split(r"(\$\{|\}|\s+)", obj)  # ${ or space or }
            ]
        )

        opener = "${"
        closer = "}"

        while True:
            last_open = None
            next_close = None
            for i, tok in enumerate(tokens):
                if not isinstance(tok, VariableValueLiteral):
                    continue
                if tok.value == opener:
                    last_open = i
                    next_close = None
                if last_open is not None and tok.value == closer and next_close is None:
                    next_close = i

            if next_close is not None:
                lookup_query = VariableValueConcatenation(
                    tokens[(cast(int, last_open) + len(opener) + 1) : next_close],
                    variable_type=variable_type,
                )
                lookup = VariableValueLookup(
                    lookup_name=tokens[cast(int, last_open) + 1],  # type: ignore
                    lookup_query=lookup_query,
                    variable_type=variable_type,
                )
                tokens[last_open : (next_close + 1)] = [lookup]  # type: ignore
            else:
                break  # cov: ignore

        return tokens.simplified

    def __iter__(self) -> Iterator[Any]:
        """How the object is iterated.

        Raises:
            NotImplementedError: Should be defined in a subclass.

        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """Return object representation.

        Raises:
            NotImplementedError: Should be defined in a subclass.

        """
        raise NotImplementedError


class VariableValueDict(VariableValue, MutableMapping[str, VariableValue]):
    """A dict variable value."""

    def __init__(
        self, data: Dict[str, Any], variable_type: VariableTypeLiteralTypeDef = "cfngin"
    ) -> None:
        """Instantiate class.

        Args:
            data: Data to be stored in the object.
            variable_type: Type of variable (cfngin|runway).

        """
        self._data = {
            k: self.parse_obj(v, variable_type=variable_type) for k, v in data.items()
        }
        self.variable_type: VariableTypeLiteralTypeDef = variable_type

    @property
    def dependencies(self) -> Set[str]:
        """Stack names that this variable depends on."""
        deps: Set[str] = set()
        for item in self.values():  # pylint: disable=no-member
            deps.update(item.dependencies)
        return deps

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved."""
        accumulator: bool = True
        for item in self.values():  # pylint: disable=no-member
            accumulator = accumulator and item.resolved
        return accumulator

    @property
    def simplified(self) -> Dict[str, Any]:
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return {k: v.simplified for k, v in self.items()}  # pylint: disable=no-member

    @property
    def value(self) -> Dict[str, Any]:
        """Value of the variable. Can be resolved or unresolved."""
        return {k: v.value for k, v in self.items()}  # pylint: disable=no-member

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        """
        for item in self.values():  # pylint: disable=no-member
            item.resolve(context, provider=provider, variables=variables, **kwargs)

    def __delitem__(self, __key: str) -> None:
        """Delete item by index."""
        del self._data[__key]

    def __getitem__(self, __key: str) -> VariableValue:
        """Get item by index."""
        return self._data[__key]

    def __iter__(self) -> Iterator[str]:
        """How the object is iterated."""
        yield from iter(self._data)

    def __len__(self) -> int:
        """Length of the object."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return object representation."""
        # pylint: disable=no-member
        return f"Dict[{', '.join(f'{k}={v}' for k, v in self.items())}]"

    def __setitem__(self, __key: str, __value: VariableValue) -> None:
        """Set item by index."""
        self._data[__key] = __value


class VariableValueList(VariableValue, MutableSequence[VariableValue]):
    """List variable value."""

    def __init__(
        self,
        iterable: Iterable[Any],
        variable_type: VariableTypeLiteralTypeDef = "cfngin",
    ) -> None:
        """Instantiate class.

        Args:
            iterable: Data to store in the iterable.
            variable_type: Type of variable (cfngin|runway).

        """
        self._data: List[VariableValue] = [
            self.parse_obj(i, variable_type=variable_type) for i in iterable
        ]
        self.variable_type: VariableTypeLiteralTypeDef = variable_type

    @property
    def dependencies(self) -> Set[str]:
        """Stack names that this variable depends on."""
        deps: Set[str] = set()
        for item in self:
            deps.update(item.dependencies)
        return deps

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved."""
        accumulator: bool = True
        for item in self:
            accumulator = accumulator and item.resolved
        return accumulator

    @property
    def simplified(self) -> List[VariableValue]:
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return [item.simplified for item in self]

    @property
    def value(self) -> List[Any]:
        """Value of the variable. Can be resolved or unresolved."""
        return [item.value for item in self]

    def insert(self, index: int, value: VariableValue) -> None:
        """Insert a value at a specific index."""
        self._data.insert(index, value)

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        """
        for item in self:
            item.resolve(context, provider=provider, variables=variables, **kwargs)

    def __delitem__(self, __index: int) -> None:
        """Delete item by index."""
        del self._data[__index]

    @overload
    def __getitem__(self, __index: int) -> VariableValue:
        ...

    @overload
    def __getitem__(self, __index: slice) -> List[VariableValue]:
        ...

    def __getitem__(  # type: ignore
        self, __index: Union[int, slice]
    ) -> Union[MutableSequence[VariableValue], VariableValue]:
        """Get item by index."""
        return self._data[__index]  # type: ignore

    @overload
    def __setitem__(self, __index: int, __value: VariableValue) -> None:
        ...

    @overload
    def __setitem__(self, __index: slice, __value: List[VariableValue]) -> None:
        ...

    def __setitem__(
        self,
        __index: Union[int, slice],
        __value: Union[List[VariableValue], VariableValue],
    ) -> None:
        """Set item by index."""
        self._data[__index] = __value  # type: ignore

    def __iter__(self) -> Iterator[VariableValue]:
        """Object iteration."""
        yield from iter(self._data)

    def __len__(self) -> int:
        """Length of the object."""
        return len(self._data)

    def __repr__(self) -> str:
        """Object string representation."""
        return f"List[{', '.join(repr(i) for i in self._data)}]"


class VariableValueLiteral(Generic[_LiteralValue], VariableValue):
    """The literal value of a variable as provided."""

    def __init__(
        self, value: _LiteralValue, variable_type: VariableTypeLiteralTypeDef = "cfngin"
    ) -> None:
        """Instantiate class.

        Args:
            value: Data to store in the object.
            variable_type: Type of variable (cfngin|runway).

        """
        self._data = value
        self.variable_type: VariableTypeLiteralTypeDef = variable_type

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved.

        The ValueLiteral will always appear as resolved because it does
        not "resolve" since it is the literal definition of the value.

        """
        return True

    @property
    def value(self) -> _LiteralValue:
        """Value of the variable."""
        return self._data

    def __iter__(self) -> Iterator[Any]:
        """How the object is iterated."""
        yield self

    def __repr__(self) -> str:
        """Return object representation."""
        return f"Literal[{self._data}]"


class VariableValueConcatenation(Generic[_VariableValue], VariableValue):
    """A concatinated variable values."""

    def __init__(
        self,
        iterable: Iterable[_VariableValue],
        variable_type: VariableTypeLiteralTypeDef = "cfngin",
    ) -> None:
        """Instantiate class.

        Args:
            iterable: Data to store in the iterable.
            variable_type: Type of variable (cfngin|runway).

        """
        self._data = list(iterable)
        self.variable_type: VariableTypeLiteralTypeDef = variable_type

    @property
    def dependencies(self) -> Set[str]:
        """Stack names that this variable depends on."""
        deps: Set[str] = set()
        for item in self:
            deps.update(item.dependencies)
        return deps

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved."""
        accumulator: bool = True
        for item in self:
            accumulator = accumulator and item.resolved
        return accumulator

    @property
    def simplified(self) -> VariableValue:
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or flatten
        nested concatentations.

        """
        concat: List[VariableValue] = []
        for item in self:
            if isinstance(item, VariableValueLiteral) and item.value == "":
                pass
            elif (
                isinstance(item, VariableValueLiteral)
                and concat
                and isinstance(concat[-1], VariableValueLiteral)
            ):
                concat[-1] = VariableValueLiteral(
                    str(concat[-1].value) + str(item.value)  # type: ignore
                )
            elif isinstance(item, VariableValueConcatenation):  # type: ignore
                concat.extend(iter(item.simplified))
            else:
                concat.append(item.simplified)

        if not concat:
            return VariableValueLiteral("")
        if len(concat) == 1:
            return concat[0]
        return VariableValueConcatenation(concat)

    @property
    def value(self) -> Any:
        """Value of the variable. Can be resolved or unresolved.

        Raises:
            InvalidLookupConcatenation

        """
        if len(self) == 1:
            return self[0].value

        values: List[str] = []
        for value in self:
            resolved_value = value.value
            if isinstance(resolved_value, bool) or not isinstance(
                resolved_value, (int, str)
            ):
                raise InvalidLookupConcatenation(value, self)
            values.append(str(resolved_value))
        return "".join(values)

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        """
        for value in self:
            value.resolve(context, provider=provider, variables=variables, **kwargs)

    def __delitem__(self, __index: int) -> None:
        """Delete item by index."""
        del self._data[__index]

    @overload
    def __getitem__(self, __index: int) -> _VariableValue:
        ...

    @overload
    def __getitem__(self, __index: slice) -> List[_VariableValue]:
        ...

    def __getitem__(
        self, __index: Union[int, slice]
    ) -> Union[List[_VariableValue], _VariableValue]:
        """Get item by index."""
        return self._data[__index]

    @overload
    def __setitem__(self, __index: int, __value: _VariableValue) -> None:
        ...

    @overload
    def __setitem__(self, __index: slice, __value: List[_VariableValue]) -> None:
        ...

    def __setitem__(
        self,
        __index: Union[int, slice],
        __value: Union[List[_VariableValue], _VariableValue],
    ) -> None:
        """Set item by index."""
        self._data[__index] = __value

    def __iter__(self) -> Iterator[_VariableValue]:
        """Object iteration."""
        yield from iter(self._data)

    def __len__(self) -> int:
        """Length of the object."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return object representation."""
        return f"Concatenation[{', '.join(repr(v) for v in self)}]"


class VariableValueLookup(VariableValue):
    """A lookup variable value."""

    handler: Type[LookupHandler]
    lookup_name: VariableValueLiteral[str]
    lookup_query: VariableValue

    _resolved: bool

    def __init__(
        self,
        lookup_name: VariableValueLiteral[str],
        lookup_query: Union[str, VariableValue],
        handler: Optional[Type[LookupHandler]] = None,
        variable_type: VariableTypeLiteralTypeDef = "cfngin",
    ) -> None:
        """Initialize class.

        Args:
            lookup_name: Name of the invoked lookup.
            lookup_query: Data portion of the lookup.
            handler: Lookup handler that will be use to resolve the value.
            variable_type: Type of variable (cfngin|runway).

        Raises:
            UnknownLookupType: Invalid lookup type.
            ValueError: Invalid value for variable_type.

        """
        self._resolved = False
        self._data = None

        self.lookup_name = lookup_name
        self.variable_type: VariableTypeLiteralTypeDef = variable_type

        if isinstance(lookup_query, str):
            lookup_query = VariableValueLiteral(lookup_query)
        self.lookup_query = lookup_query

        if handler is None:
            lookup_name_resolved = lookup_name.value
            try:
                if variable_type == "cfngin":
                    handler = CFNGIN_LOOKUP_HANDLERS[lookup_name_resolved]
                elif variable_type == "runway":
                    handler = RUNWAY_LOOKUP_HANDLERS[lookup_name_resolved]
                else:
                    raise ValueError(
                        'Variable type must be one of "cfngin" or "runway"'
                    )
            except KeyError:
                raise UnknownLookupType(self) from None
        self.handler = handler

    @property
    def dependencies(self) -> Set[str]:
        """Stack names that this variable depends on."""
        if hasattr(self.handler, "dependencies"):
            return self.handler.dependencies(self.lookup_query)
        return set()

    @property
    def resolved(self) -> bool:
        """Use to check if the variable value has been resolved."""
        return self._resolved

    @property
    def simplified(self) -> VariableValueLookup:
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return self

    @property
    def value(self) -> Any:
        """Value of the variable. Can be resolved or unresolved.

        Raises:
            UnresolvedVariableValue: Value accessed before it has been resolved.

        """
        if self._resolved:
            return self._data
        raise UnresolvedVariableValue(self)

    def resolve(
        self,
        context: Union[CfnginContext, RunwayContext],
        provider: Optional[Provider] = None,
        variables: Optional[RunwayVariablesDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Resolve the variable value.

        Args:
            context: The current context object.
            provider: Subclass of the base provider.
            variables: Object containing variables passed to Runway.

        Raises:
            FailedLookup: A lookup failed for any reason.

        """
        self.lookup_query.resolve(
            context=context, provider=provider, variables=variables, **kwargs
        )
        try:
            result = self.handler.handle(
                self.lookup_query.value,
                context=context,
                provider=provider,
                variables=variables,
                **kwargs,
            )
            return self._resolve(result)
        except Exception as err:
            raise FailedLookup(self, err) from err

    def __iter__(self) -> Iterator[VariableValueLookup]:
        """How the object is iterated."""
        yield self

    def __repr__(self) -> str:
        """Return object representation."""
        if self._resolved:
            return (
                f"Lookup[{self._data} ({self.lookup_name} {repr(self.lookup_query)})]"
            )
        return f"Lookup[{self.lookup_name} {repr(self.lookup_query)}]"

    def __str__(self) -> str:
        """Object displayed as a string."""
        return f"${{{self.lookup_name.value} {self.lookup_query.value}}}"
