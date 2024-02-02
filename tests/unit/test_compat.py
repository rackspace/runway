"""Test runway.compat."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import call

import pytest

from runway.compat import shlex_join

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.compat"

py37 = pytest.mark.skipif(
    sys.version_info >= (3, 8), reason="requires python3.8 or higher"
)


@py37
def test_shlex_join(mocker: MockerFixture) -> None:
    """Test shlex_join."""
    mock_quote = mocker.patch(f"{MODULE}.shlex.quote", return_value="q")
    assert shlex_join(["foo", "bar"])
    mock_quote.assert_has_calls([call("foo"), call("bar")])
