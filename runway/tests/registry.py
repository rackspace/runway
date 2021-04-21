"""Register test handlers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

from .handlers import cfn_lint, script
from .handlers import yaml_lint as yamllint

if TYPE_CHECKING:
    from .handlers.base import TestHandler

TEST_HANDLERS: Dict[str, Type[TestHandler]] = {}


def register_test_handler(test_type: str, handler: Type[TestHandler]) -> None:
    """Register a test handler.

    Args:
        test_type: Name to register the handler under.
        handler: Test handler class.

    """
    TEST_HANDLERS[test_type] = handler


def unregister_test_handler(test_type: str) -> None:
    """Unregister the specified test type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        test_type (str): Name of the lookup type to unregister.

    """
    TEST_HANDLERS.pop(test_type, None)


register_test_handler(script.TYPE_NAME, script.ScriptHandler)
register_test_handler(cfn_lint.TYPE_NAME, cfn_lint.CfnLintHandler)
register_test_handler(yamllint.TYPE_NAME, yamllint.YamllintHandler)
