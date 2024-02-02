"""Mock hook."""

from typing import Any, Dict


def mock_hook(*, value: Any, **_: Any) -> Dict[str, Any]:
    """Mock hook.

    Returns:
        {'result': kwargs['value']}

    """
    return {"result": value}
