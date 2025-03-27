"""Test classes."""

from __future__ import annotations

import os  # imports os
from typing import TYPE_CHECKING, Any, cast

from click.testing import CliRunner

if TYPE_CHECKING:
    import pytest


def cli_runner_factory(request: pytest.FixtureRequest) -> CliRunner:
    """Initialize instance of `click.testing.CliRunner`."""
    kwargs: dict[str, Any] = {
        "env": {
            "CFNGIN_STACK_POLL_TIME": "1",
            "DEPLOY_ENVIRONMENT": "test",
            "RUNWAY_COLORIZE": "1",
            **os.environ,
        }
    }
    mark = cast("pytest.Function | pytest.Item", request.node).get_closest_marker("cli_runner")
    if mark:
        kwargs.update(cast("dict[str, Any]", mark.kwargs))
    return CliRunner(**kwargs)
