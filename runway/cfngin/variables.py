"""CFNgin variables."""
import re

from six import string_types

from .exceptions import (FailedLookup, FailedVariableLookup,
                         InvalidLookupCombination, InvalidLookupConcatenation,
                         UnknownLookupType, UnresolvedVariable,
                         UnresolvedVariableValue)
from .lookups.registry import LOOKUP_HANDLERS


def resolve_variables(variables, context, provider):
    """Given a list of variables, resolve all of them.

    Args:
        variables (List[:class:`Variable`]): List of variables.
        context (:class:`runway.cfngin.context.Context`): CFNgin context.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Subclass
            of the base provider.

    """
    for variable in variables:
        variable.resolve(context, provider)


class Variable(object):
    """Represents a variable passed to a stack."""

    def __init__(self, name, value):
        """Instantiate class.

        Args:
            name (str): Name of the variable
            value (Any): Initial value of the variable from the config.
                (str, list, dict)

        """
        self.name = name
        self._raw_value = value
        self._value = VariableValue.parse(value)

    @property
    def value(self):
        """Return the current value of the Variable."""
        try:
            return self._value.value
        except UnresolvedVariableValue:
            raise UnresolvedVariable("<unknown>", self)
        except InvalidLookupConcatenation as err:
            raise InvalidLookupCombination(err.lookup, err.lookups, self)

    @property
    def resolved(self):
        """Boolean for whether the Variable has been resolved.

        Variables only need to be resolved if they contain lookups.

        """
        return self._value.resolved

    def resolve(self, context, provider):
        """Recursively resolve any lookups with the Variable.

        Args:
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                subclass of the base provider

        """
        try:
            self._value.resolve(context, provider)
        except FailedLookup as err:
            raise FailedVariableLookup(self.name, err.lookup, err.error)

    @property
    def dependencies(self):
        """Stack names that this variable depends on.

        Returns:
            Set[str]: Stack names that this variable depends on.

        """
        return self._value.dependencies


class VariableValue(object):
    """Abstract Syntax Tree base object to parse the value for a variable."""

    @property
    def value(self):
        """Abstract method for a variable value's value."""
        raise NotImplementedError

    def __iter__(self):
        """Abstract method for iterating over an instance of this class."""
        raise NotImplementedError

    @property
    def resolved(self):
        """Abstract method for variable is resolved.

        Returns:
            bool: Whether value() will not raise an error.

        """
        raise NotImplementedError

    def resolve(self, context, provider):
        """Resolve the value of the variable."""

    @property
    def dependencies(self):
        """Stack names that this variable depends on."""
        return set()

    @property
    def simplified(self):
        """Return a simplified version of the value.

        This can be used to e.g. concatenate two literals in to one literal, or
        to flatten nested Concatenations

        Returns:
            VariableValue

        """
        return self

    @classmethod
    def parse(cls, input_object):
        """Parse complex variable structures using type appropriate subclasses.

        Args:
            input_object (Any): The objected defined as the value of a
                variable.

        """
        if isinstance(input_object, list):
            return VariableValueList.parse(input_object)
        if isinstance(input_object, dict):
            return VariableValueDict.parse(input_object)
        if not isinstance(input_object, string_types):
            return VariableValueLiteral(input_object)
        # else:  # str

        tokens = VariableValueConcatenation([
            VariableValueLiteral(t)
            for t in re.split(r'(\$\{|\}|\s+)', input_object)
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
                if last_open is not None and \
                        tok.value == closer and \
                        next_close is None:
                    next_close = i

            if next_close is not None:
                lookup_data = VariableValueConcatenation(
                    tokens[(last_open + len(opener) + 1):next_close]
                )
                lookup = VariableValueLookup(
                    lookup_name=tokens[last_open + 1],
                    lookup_data=lookup_data,
                )
                tokens[last_open:(next_close + 1)] = [lookup]
            else:
                break

        tokens = tokens.simplified

        return tokens


class VariableValueLiteral(VariableValue):
    """The literal value of a variable as provided."""

    def __init__(self, value):
        """Instantiate class."""
        self._value = value

    @property
    def value(self):
        """Value of the variable. Can be resolved or unresolved."""
        return self._value

    @property
    def resolved(self):
        """Use to check if the variable value has been resolved.

        The ValueLiteral will always appear as resolved because it does
        not "resolve" since it is the literal definition of the value.

        """
        return True

    def __iter__(self):
        """How the object is iterated."""
        yield self

    def __repr__(self):
        """Object represented as a string."""
        return "Literal<{}>".format(repr(self._value))


class VariableValueList(VariableValue, list):
    """A list variable value."""

    @classmethod
    def parse(cls, input_object):
        """Parse list variable structure.

        Args:
            input_object (List[Any]): The objected defined as the value of a
                variable.

        """
        acc = [
            VariableValue.parse(obj)
            for obj in input_object
        ]
        return cls(acc)

    @property
    def value(self):
        """Value of the variable. Can be resolved or unresolved."""
        return [
            item.value
            for item in self
        ]

    @property
    def resolved(self):
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self:
            accumulator = accumulator and item.resolved
        return accumulator

    def resolve(self, context, provider):
        """Resolve the variable value.

        Args:
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                subclass of the base provider

        """
        for item in self:
            item.resolve(context, provider)

    @property
    def dependencies(self):
        """Stack names that this variable depends on."""
        deps = set()
        for item in self:
            deps.update(item.dependencies)
        return deps

    @property
    def simplified(self):
        """Return a simplified version of the value.

        This can be used to concatenate two literals into one literal or
        flatten nested concatenations.

        """
        return [
            item.simplified
            for item in self
        ]

    def __iter__(self):
        """How the object is iterated."""
        return list.__iter__(self)

    def __repr__(self):
        """Object represented as a string."""
        return "List[{}]".format(', '.join([repr(value) for value in self]))


class VariableValueDict(VariableValue, dict):
    """A dict variable value."""

    @classmethod
    def parse(cls, input_object):
        """Parse dict variable structure.

        Args:
            input_object (Dict[str, Any]): The objected defined as the value
                of a variable.

        """
        acc = {
            k: VariableValue.parse(v)
            for k, v in input_object.items()
        }
        return cls(acc)

    @property
    def value(self):
        """Value of the variable. Can be resolved or unresolved."""
        return {
            k: v.value
            for k, v in self.items()
        }

    @property
    def resolved(self):
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self.values():
            accumulator = accumulator and item.resolved
        return accumulator

    def resolve(self, context, provider):
        """Resolve the variable value.

        Args:
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                subclass of the base provider

        """
        for item in self.values():
            item.resolve(context, provider)

    @property
    def dependencies(self):
        """Stack names that this variable depends on."""
        deps = set()
        for item in self.values():
            deps.update(item.dependencies)
        return deps

    @property
    def simplified(self):
        """Return a simplified version of the value."""
        return {
            k: v.simplified
            for k, v in self.items()
        }

    def __iter__(self):
        """How the object is iterated."""
        return dict.__iter__(self)

    def __repr__(self):
        """Object represented as a string."""
        return "Dict[{}]".format(', '.join([
            "{}={}".format(k, repr(v)) for k, v in self.items()
        ]))


class VariableValueConcatenation(VariableValue, list):
    """A concatinated variable value."""

    @property
    def value(self):
        """Value of the variable. Can be resolved or unresolved."""
        if len(self) == 1:
            return self[0].value

        values = []
        for value in self:
            resolved_value = value.value
            if not isinstance(resolved_value, string_types):
                raise InvalidLookupConcatenation(value, self)
            values.append(resolved_value)
        return ''.join(values)

    @property
    def resolved(self):
        """Use to check if the variable value has been resolved."""
        accumulator = True
        for item in self:
            accumulator = accumulator and item.resolved
        return accumulator

    def resolve(self, context, provider):
        """Resolve the variable value.

        Args:
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                subclass of the base provider

        """
        for value in self:
            value.resolve(context, provider)

    @property
    def dependencies(self):
        """Stack names that this variable depends on."""
        deps = set()
        for item in self:
            deps.update(item.dependencies)
        return deps

    @property
    def simplified(self):
        """Return a simplified version of the value."""
        concat = []
        for item in self:
            if isinstance(item, VariableValueLiteral) and item.value == '':
                continue

            if (isinstance(item, VariableValueLiteral) and concat and
                    isinstance(concat[-1], VariableValueLiteral)):
                # Join the literals together
                concat[-1] = VariableValueLiteral(
                    concat[-1].value + item.value
                )

            elif isinstance(item, VariableValueConcatenation):
                # Flatten concatenations
                concat.extend(item.simplified)

            else:
                concat.append(item.simplified)

        if not concat:
            return VariableValueLiteral('')
        if len(concat) == 1:
            return concat[0]
        return VariableValueConcatenation(concat)

    def __iter__(self):
        """How the object is iterated."""
        return list.__iter__(self)

    def __repr__(self):
        """Object represented as a string."""
        return "Concat[{}]".format(', '.join([repr(value) for value in self]))


class VariableValueLookup(VariableValue):
    """A lookup variable value."""

    def __init__(self, lookup_name, lookup_data, handler=None):
        """Instantiate class.

        Args:
            lookup_name (str): Name of the invoked lookup.
            lookup_data (:class:`VariableValue`): Data portion of the lookup.

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
                handler = LOOKUP_HANDLERS[lookup_name_resolved]
            except KeyError:
                raise UnknownLookupType(lookup_name_resolved)
        self.handler = handler

    def resolve(self, context, provider):
        """Resolve the variable value.

        Args:
            context (:class:`runway.cfngin.context.Context`): Current context
                for building the stack
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                subclass of the base provider

        """
        self.lookup_data.resolve(context, provider)
        try:
            if isinstance(self.handler, type):
                # Hander is a new-style handler
                result = self.handler.handle(
                    value=self.lookup_data.value,
                    context=context,
                    provider=provider
                )
            else:
                result = self.handler(
                    value=self.lookup_data.value,
                    context=context,
                    provider=provider
                )
            self._resolve(result)
        except Exception as err:
            raise FailedLookup(self, err)

    def _resolve(self, value):
        self._value = value
        self._resolved = True

    @property
    def dependencies(self):
        """Stack names that this variable depends on."""
        if isinstance(self.handler, type):
            return self.handler.dependencies(self.lookup_data)
        return set()

    @property
    def value(self):
        """Value of the variable. Can be resolved or unresolved."""
        if self._resolved:
            return self._value
        raise UnresolvedVariableValue(self)

    def resolved(self):
        """Use to check if the variable value has been resolved."""
        return self._resolved

    @property
    def simplified(self):
        """Return a simplified version of the value."""
        return VariableValueLookup(
            lookup_name=self.lookup_name,
            lookup_data=self.lookup_data.simplified,
        )

    def __iter__(self):
        """How the object is iterated."""
        yield self

    def __repr__(self):
        """Object represented as a string."""
        if self._resolved:
            return "Lookup<{r} ({t} {d})>".format(
                r=self._value,
                t=self.lookup_name,
                d=repr(self.lookup_data),
            )
        return "Lookup<{t} {d}>".format(
            t=self.lookup_name,
            d=repr(self.lookup_data),
        )

    def __str__(self):
        """Object displayed as a string."""
        return "${{{type} {data}}}".format(
            type=self.lookup_name.value,
            data=self.lookup_data.value,
        )
