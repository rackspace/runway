"""Test classes."""

# pyright: basic, reportIncompatibleMethodOverride=none
from __future__ import annotations

import os  # imports os
from typing import TYPE_CHECKING, Any, Dict, cast

from click.testing import CliRunner

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest


def cli_runner_factory(request: SubRequest) -> CliRunner:
    """Initialize instance of `click.testing.CliRunner`."""
    kwargs: Dict[str, Any] = {
        "env": {
            "CFNGIN_STACK_POLL_TIME": "1",
            "DEPLOY_ENVIRONMENT": "test",
            "RUNWAY_COLORIZE": "1",
            **os.environ,
        }
    }
    mark = request.node.get_closest_marker("cli_runner")
    if mark:
        kwargs.update(cast(Dict[str, Any], mark.kwargs))
    return CliRunner(**kwargs)
