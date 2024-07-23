"""Test runway.cfngin.blueprints.variables.types."""

from __future__ import annotations

import re

import pytest

from runway.cfngin.blueprints.variables.types import CFNType

PATTERN_LIST = r"(AWS|CFN)?(?P<type>.*)List?"
PATTERN_SUB_AWS_PARAMETER_TYPE = r"(AWS|::)"

AWS_CLASSES = [kls for kls in CFNType.__subclasses__() if not kls.__name__.startswith("CFN")]
CFN_CLASSES = [kls for kls in CFNType.__subclasses__() if kls.__name__.startswith("CFN")]


def handle_ssm_parameter_value(value: str) -> str:
    """Handle SSMParameterValue types."""
    if "SSMParameterValue" in value:
        return f"SSMParameterValue<{value.replace('SSMParameterValue', '')}>"
    return value


@pytest.mark.parametrize("kls", AWS_CLASSES)
def test_aws_types(kls: type[CFNType]) -> None:
    """Test variable types for parameter types beginning with ``AWS::``.

    This does not test the formatting of the value.

    """
    if kls.__name__.endswith("List") and "CommaDelimited" not in kls.__name__:
        match = re.search(PATTERN_LIST, kls.__name__)
        assert match
        assert re.sub(
            PATTERN_SUB_AWS_PARAMETER_TYPE, "", kls.parameter_type
        ) == handle_ssm_parameter_value(f"List<{match.group('type')}>")
    else:
        assert re.sub(
            PATTERN_SUB_AWS_PARAMETER_TYPE, "", kls.parameter_type
        ) == handle_ssm_parameter_value(kls.__name__)


@pytest.mark.parametrize("kls", CFN_CLASSES)
def test_cfn_types(kls: type[CFNType]) -> None:
    """Test variable types beginning with CFN."""
    if kls.__name__.endswith("List") and "CommaDelimited" not in kls.__name__:
        match = re.search(PATTERN_LIST, kls.__name__)
        assert match
        assert kls.parameter_type == f"List<{match.group('type')}>"
    else:
        assert kls.parameter_type == kls.__name__[3:]
