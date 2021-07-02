"""File lookup."""
# pylint: disable=arguments-differ
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import base64
import collections.abc
import json
import re
from typing import Any, Callable, Dict, List, Mapping, Sequence, Union, overload

import yaml
from troposphere import Base64, GenericHelperFn
from typing_extensions import Literal

from ....lookups.handlers.base import LookupHandler
from ...utils import read_value_from_path

TYPE_NAME = "file"

_PARAMETER_PATTERN = re.compile(r"{{([::|\w]+)}}")

ParameterizedObjectTypeDef = Union[bytes, str, Mapping[str, Any], Sequence[Any], Any]
ParameterizedObjectReturnTypeDef = Union[
    Dict[str, "ParameterizedObjectReturnTypeDef"],
    GenericHelperFn,
    List["ParameterizedObjectReturnTypeDef"],
]


class FileLookup(LookupHandler):
    """File lookup."""

    @classmethod
    def handle(cls, value: str, **_: Any) -> Any:
        r"""Translate a filename into the file contents.

        Args:
            value: Parameter(s) given to this lookup.

        Fields should use the following format::

            <codec>:<path>

        Example::

            # We've written a file to /some/path:
            $ echo "hello there" > /some/path

            # With CFNgin we would reference the contents of this file with the
            # following
            conf_key: ${file plain:file://some/path}

            # The above would resolve to
            conf_key: hello there

            # Or, if we used wanted a base64 encoded copy of the file data
            conf_key: ${file base64:file://some/path}

            # The above would resolve to
            conf_key: aGVsbG8gdGhlcmUK

        Supported codecs:

        **plain**
            Plain Text

        **base64**
            Encode the plain text file at the given path with base64 prior to
            returning it.

        **parameterized**
            The same as plain, but additionally supports referencing template
            parameters to create userdata that's supplemented with information
            from the template, as is commonly needed in EC2 UserData.
            For example, given a template parameter of BucketName, the file
            could contain the following text::

                #!/bin/sh
                aws s3 sync s3://{{BucketName}}/somepath /somepath

            Then you could use something like this in the YAML config
            file::

                UserData: ${file parameterized:/path/to/file}

            Resulting in the UserData parameter being defined as::

                { "Fn::Join" : ["", [
                    "#!/bin/sh\\naws s3 sync s3://",
                    {"Ref" : "BucketName"},
                    "/somepath /somepath"
                ]] }

        **parameterized-b64**
            The same as parameterized, with the results additionally wrapped
            in ``{ "Fn::Base64": ... }`` , which is what you actually need
            for EC2 UserData.

            When using parameterized-b64 for UserData, you should use a
            variable defined as such:

            .. code-block:: python

                from troposphere import AWSHelperFn

                "UserData": {
                    "type": AWSHelperFn,
                    "description": "Instance user data",
                    "default": Ref("AWS::NoValue")
                }

            Then assign UserData in a LaunchConfiguration or Instance to
            ``self.variables["UserData"]``. Note that we use AWSHelperFn
            as the type because the parameterized-b64 codec returns either a
            Base64 or a GenericHelperFn troposphere object.

        **json**
            Decode the file as JSON and return the resulting object

        **json-parameterized**
            Same as ``json``, but applying templating rules from
            ``parameterized`` to every object *value*. Note that
            object *keys* are not modified. Example (an external
            PolicyDocument)::

                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "some:Action"
                                ],
                                "Resource": "{{MyResource}}"
                            }
                        ]
                    }

        **yaml**
            Decode the file as YAML and return the resulting object.
            All strings are returned as ``unicode`` even in Python 2.

        **yaml-parameterized**
            Same as ``json-parameterized``, but using YAML. Example::

                Version: 2012-10-17
                Statement:
                  - Effect: Allow
                    Action:
                      - "some:Action"
                    Resource: "{{MyResource}}"

        """
        try:
            codec, path = value.split(":", 1)
        except ValueError:
            raise TypeError(
                f'File value must be of the format "<codec>:<path>" (got {value})'
            ) from None
        return CODECS[codec](read_value_from_path(path))


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
    parts: List[Any] = []
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
def parameterized_codec(
    raw: Union[bytes, str], b64: Literal[False] = ...
) -> GenericHelperFn:
    ...


@overload
def parameterized_codec(raw: Union[bytes, str], b64: Literal[True] = ...) -> Base64:
    ...


def parameterized_codec(raw: Union[bytes, str], b64: bool = False) -> Any:
    """Parameterize a string, possibly encoding it as Base64 afterwards.

    Args:
        raw: String to be processed. Byte strings will be interpreted as UTF-8.
        b64: Whether to wrap the output in a Base64 CloudFormation call.

    Returns:
        :class:`troposphere.AWSHelperFn`: Output to be included in a
        CloudFormation template.

    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    result = _parameterize_string(raw)

    # Note, since we want a raw JSON object (not a string) output in the
    # template, we wrap the result in GenericHelperFn (not needed if we're
    # using Base64)
    return Base64(result.data) if b64 else result


@overload
def _parameterize_obj(obj: Union[bytes, str]) -> GenericHelperFn:
    ...


@overload
def _parameterize_obj(obj: Mapping[str, Any]) -> ParameterizedObjectReturnTypeDef:
    ...


@overload
def _parameterize_obj(obj: List[Any]) -> ParameterizedObjectReturnTypeDef:
    ...


def _parameterize_obj(
    obj: ParameterizedObjectTypeDef,
) -> ParameterizedObjectReturnTypeDef:
    """Recursively parameterize all strings contained in an object.

    Parametrizes all values of a Mapping, all items of a Sequence, an
    unicode string, or pass other objects through unmodified.

    Byte strings will be interpreted as UTF-8.

    Args:
        obj: Data to parameterize.

    Return:
        A parameterized object to be included in a CloudFormation template.
        Mappings are converted to `dict`, Sequences are converted to  `list`,
        and strings possibly replaced by compositions of function calls.

    """
    if isinstance(obj, bytes):
        return _parameterize_string(obj.decode("utf8"))
    if isinstance(obj, str):
        return _parameterize_string(obj)
    if isinstance(obj, collections.abc.Mapping):
        return {key: _parameterize_obj(value) for key, value in obj.items()}
    if isinstance(obj, collections.abc.Sequence):
        return [_parameterize_obj(item) for item in obj]
    return obj


class SafeUnicodeLoader(yaml.SafeLoader):
    """Safe unicode loader."""

    def construct_yaml_str(self, node: Any) -> Any:
        """Construct yaml str."""
        return self.construct_scalar(node)


def yaml_codec(raw: str, parameterized: bool = False) -> Any:
    """YAML codec."""
    data = yaml.load(raw, Loader=SafeUnicodeLoader)
    return _parameterize_obj(data) if parameterized else data


def json_codec(raw: str, parameterized: bool = False) -> Any:
    """JSON codec."""
    data = json.loads(raw)
    return _parameterize_obj(data) if parameterized else data


CODECS: Dict[str, Callable[..., Any]] = {
    "plain": lambda x: x,
    "base64": lambda x: base64.b64encode(x.encode("utf8")).decode("utf-8"),
    "parameterized": lambda x: parameterized_codec(x, False),
    "parameterized-b64": lambda x: parameterized_codec(x, True),
    "yaml": lambda x: yaml_codec(x, parameterized=False),
    "yaml-parameterized": lambda x: yaml_codec(x, parameterized=True),
    "json": lambda x: json_codec(x, parameterized=False),
    "json-parameterized": lambda x: json_codec(x, parameterized=True),
}
