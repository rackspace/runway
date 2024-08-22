"""Mock hook."""

from typing import Any


def mock_hook(*, value: Any, **_: Any) -> dict[str, Any]:
    """Mock hook.

    Returns:
        {'result': kwargs['value']}

    """
    return {"result": value}
