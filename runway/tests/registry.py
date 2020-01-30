"""Register test handlers."""
# modeled after https://github.com/cloudtools/stacker/blob/master/stacker/lookups/registry.py
from past.builtins import basestring

from ..util import load_object_from_string

from .handlers import script
from .handlers import cfn_lint
from .handlers import yaml_lint as yamllint


TEST_HANDLERS = {}


def register_test_handler(test_type, handler_or_path):
    """Register a test handler.

    Args:
        test_type (str): Name to register the handler under
        handler_path (OneOf[func, str]): a function or a path to a handler

    """
    handler = handler_or_path
    if isinstance(handler_or_path, basestring):
        handler = load_object_from_string(handler_or_path)
    TEST_HANDLERS[test_type] = handler


def unregister_test_handler(test_type):
    """Unregister the specified test type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        test_type (str): Name of the lookup type to unregister

    """
    TEST_HANDLERS.pop(test_type, None)


register_test_handler(script.TYPE_NAME, script.ScriptHandler)
register_test_handler(cfn_lint.TYPE_NAME, cfn_lint.CfnLintHandler)
register_test_handler(yamllint.TYPE_NAME, yamllint.YamllintHandler)
