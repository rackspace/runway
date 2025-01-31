"""Copy of ``awscli.customizations.cloudformation.yamlhelper.py``."""

# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from __future__ import annotations

import json
from collections.abc import MutableMapping, MutableSequence
from typing import Any, cast

import yaml


def intrinsics_multi_constructor(
    loader: yaml.Loader,
    tag_prefix: str,  # noqa: ARG001
    node: yaml.Node,
) -> dict[str, Any]:
    """YAML constructor to parse CloudFormation intrinsics.

    This will return a dictionary with key being the intrinsic name

    """
    # Get the actual tag name excluding the first exclamation
    tag = node.tag[1:]

    # Some intrinsic functions doesn't support prefix "Fn::"
    prefix = "Fn::"
    if tag in ["Ref", "Condition"]:
        prefix = ""

    cfntag = prefix + tag

    if tag == "GetAtt" and isinstance(node.value, str):
        # ShortHand notation for !GetAtt accepts Resource.Attribute format
        # while the standard notation is to use an array
        # [Resource, Attribute]. Convert shorthand to standard format
        value = node.value.split(".", 1)

    elif isinstance(node, yaml.ScalarNode):
        # Value of this node is scalar
        value = loader.construct_scalar(node)

    elif isinstance(node, yaml.SequenceNode):
        # Value of this node is an array (Ex: [1,2])
        value = cast(MutableSequence[Any], loader.construct_sequence(node))

    else:
        # Value of this node is an mapping (ex: {foo: bar})
        value = cast(MutableMapping[Any, Any], loader.construct_mapping(node))  # type: ignore

    return {cfntag: value}


def yaml_dump(dict_to_dump: dict[str, Any]) -> str:
    """Dump the dictionary as a YAML document."""
    return yaml.safe_dump(dict_to_dump, default_flow_style=False)


def yaml_parse(yamlstr: str) -> dict[str, Any]:
    """Parse a yaml string."""
    try:
        # PyYAML doesn't support json as well as it should, so if the input
        # is actually just json it is better to parse it with the standard
        # json parser.
        return json.loads(yamlstr)
    except ValueError:
        yaml.SafeLoader.add_multi_constructor("!", intrinsics_multi_constructor)
        return yaml.safe_load(yamlstr)
