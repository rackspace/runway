"""File lookup."""

from __future__ import annotations

import base64
import collections.abc
import json
import re
from typing import TYPE_CHECKING, Any, Callable, ClassVar, overload

import yaml
from pydantic import field_validator
from troposphere import Base64, GenericHelperFn

from ....lookups.handlers.base import LookupHandler
from ....utils import BaseModel
from ...utils import read_value_from_path

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from typing_extensions import Literal, TypeAlias

    from ....lookups.handlers.base import ParsedArgsTypeDef

_PARAMETER_PATTERN = re.compile(r"{{([::|\w]+)}}")

ParameterizedObjectTypeDef: TypeAlias = "str | Mapping[str, Any] | Sequence[Any] | Any"
ParameterizedObjectReturnTypeDef: TypeAlias = (
    "dict[str, ParameterizedObjectReturnTypeDef] | GenericHelperFn | list[ParameterizedObjectReturnTypeDef]"
)


class ArgsDataModel(BaseModel):
    """Arguments data model."""

    codec: str
    """Codec that will be used to parse and/or manipulate the data."""

    @field_validator("codec")
    @classmethod
    def _validate_supported_codec(cls, v: str) -> str:
        """Validate that the selected codec is supported."""
        if v in CODECS:
            return v
        raise ValueError(f"Codec '{v}' must be one of: {', '.join(CODECS)}")


class FileLookup(LookupHandler[Any]):
    """File lookup."""

    TYPE_NAME: ClassVar[str] = "file"
    """Name that the Lookup is registered as."""

    @classmethod
    def parse(cls, value: str) -> tuple[str, ParsedArgsTypeDef]:
        """Parse the value passed to the lookup.

        This overrides the default parsing to account for special requirements.

        Args:
            value: The raw value passed to a lookup.

        Returns:
            The lookup query and a dict of arguments

        Raises:
            ValueError: The value provided does not match the expected regex.

        """
        args: ParsedArgsTypeDef = {}
        try:
            args["codec"], data_or_path = value.split(  # pyright: ignore[reportGeneralTypeIssues]
                ":", 1
            )
        except ValueError:
            raise ValueError(
                rf"Query '{value}' doesn't match regex: ^(?P<codec>[{'|'.join(CODECS)}]:.+$)"
            ) from None
        return read_value_from_path(data_or_path), args

    @classmethod
    def handle(cls, value: str, *_args: Any, **_kwargs: Any) -> Any:
        """Translate a filename into the file contents."""
        data, raw_args = cls.parse(value)
        args = ArgsDataModel.model_validate(raw_args)
        return CODECS[args.codec](data)


def _parameterize_string(raw: str) -> GenericHelperFn:
    """Substitute placeholders in a string using CloudFormation references.

    Args:
        raw: String to be processed. Byte strings are not supported; decode them
        before passing them to this function.

    Returns:
        An expression with placeholders from the input replaced, suitable to be
        passed to Troposphere to be included in CloudFormation template.
        This will be the input string without modification if no substitutions
        are found, and a composition of CloudFormation calls otherwise.

    """
    parts: list[Any] = []
    s_index = 0

    for match in _PARAMETER_PATTERN.finditer(raw):
        parts.append(raw[s_index : match.start()])
        parts.append({"Ref": match.group(1)})
        s_index = match.end()

    if not parts:
        return GenericHelperFn(raw)

    parts.append(raw[s_index:])
    return GenericHelperFn({"Fn::Join": ["", parts]})


@overload
def parameterized_codec(raw: str, b64: Literal[False] = ...) -> GenericHelperFn: ...


@overload
def parameterized_codec(raw: str, b64: Literal[True] = ...) -> Base64: ...


def parameterized_codec(raw: str, b64: bool = False) -> Any:
    """Parameterize a string, possibly encoding it as Base64 afterwards.

    Args:
        raw: String to be processed. Byte strings will be interpreted as UTF-8.
        b64: Whether to wrap the output in a Base64 CloudFormation call.

    Returns:
        :class:`troposphere.AWSHelperFn`: Output to be included in a
        CloudFormation template.

    """
    result = _parameterize_string(raw)
    # Note, since we want a raw JSON object (not a string) output in the
    # template, we wrap the result in GenericHelperFn (not needed if we're
    # using Base64)
    return Base64(result.data) if b64 else result


@overload
def _parameterize_obj(obj: bytes | str) -> GenericHelperFn: ...


@overload
def _parameterize_obj(obj: Mapping[str, Any]) -> ParameterizedObjectReturnTypeDef: ...


@overload
def _parameterize_obj(obj: list[Any]) -> ParameterizedObjectReturnTypeDef: ...


def _parameterize_obj(
    obj: ParameterizedObjectTypeDef,
) -> ParameterizedObjectReturnTypeDef:
    """Recursively parameterize all strings contained in an object.

    Parametrizes all values of a Mapping, all items of a Sequence, an
    unicode string, or pass other objects through unmodified.

    Args:
        obj: Data to parameterize.

    Return:
        A parameterized object to be included in a CloudFormation template.
        Mappings are converted to `dict`, Sequences are converted to  `list`,
        and strings possibly replaced by compositions of function calls.

    """
    if isinstance(obj, str):
        return _parameterize_string(obj)
    if isinstance(obj, collections.abc.Mapping):
        return {key: _parameterize_obj(value) for key, value in obj.items()}
    if isinstance(obj, collections.abc.Sequence):
        return [_parameterize_obj(item) for item in obj]
    return obj


def yaml_codec(raw: str, parameterized: bool = False) -> Any:
    """YAML codec."""
    data: Mapping[str, Any] = yaml.load(raw, Loader=yaml.SafeLoader)
    return _parameterize_obj(data) if parameterized else data


def json_codec(raw: str, parameterized: bool = False) -> Any:
    """JSON codec."""
    data: Mapping[str, Any] = json.loads(raw)
    return _parameterize_obj(data) if parameterized else data


CODECS: dict[str, Callable[[str], Any]] = {
    "base64": lambda x: base64.b64encode(x.encode("utf8")).decode("utf-8"),
    "json": lambda x: json_codec(x, parameterized=False),
    "json-parameterized": lambda x: json_codec(x, parameterized=True),
    "parameterized": lambda x: parameterized_codec(x, False),
    "parameterized-b64": lambda x: parameterized_codec(x, True),
    "plain": lambda x: x,
    "yaml": lambda x: yaml_codec(x, parameterized=False),
    "yaml-parameterized": lambda x: yaml_codec(x, parameterized=True),
}
