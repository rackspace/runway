"""Test runway.cfngin.exceptions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

import pytest

from runway.cfngin.exceptions import (
    CfnginBucketRequired,
    InvalidConfig,
    PersistentGraphLocked,
    PersistentGraphUnlocked,
)

if TYPE_CHECKING:
    from runway.type_defs import AnyPath


class TestCfnginBucketRequired:
    """Test CfnginBucketRequired."""

    @pytest.mark.parametrize(
        "config_path, reason, expected",
        [
            (None, None, ""),
            ("./test", None, f" ({Path('./test')})"),
            (Path("/tmp"), "something", f"; something ({Path('/tmp')})"),
        ],
    )
    def test___init__(
        self, config_path: Optional[AnyPath], reason: Optional[str], expected: str
    ) -> None:
        """Test __init__."""
        expected_msg = f"cfngin_bucket is required{expected}"
        obj = CfnginBucketRequired(config_path=config_path, reason=reason)
        assert obj.message == expected_msg
        if config_path:
            if isinstance(config_path, str):
                assert obj.config_path == Path(config_path)
            else:
                assert obj.config_path == config_path


class TestInvalidConfig:
    """Test InvalidConfig."""

    @pytest.mark.parametrize(
        "errors, expected_msg",
        [("error", "error"), (["error0", "error1"], "error0\nerror1")],
    )
    def test___init__(
        self, errors: Union[str, List[Union[Exception, str]]], expected_msg: str
    ) -> None:
        """Test __init__."""
        obj = InvalidConfig(errors)
        assert obj.errors == errors
        assert obj.message == expected_msg


class TestPersistentGraphLocked:
    """Test PersistentGraphLocked."""

    @pytest.mark.parametrize(
        "message, reason, expected_msg",
        [
            (
                None,
                None,
                "Persistent graph is locked. This action requires the graph to "
                "be unlocked to be executed.",
            ),
            ("message", None, "message"),
            ("message", "reason", "message"),
            (None, "reason", "Persistent graph is locked. reason"),
        ],
    )
    def test___init__(
        self, message: Optional[str], reason: Optional[str], expected_msg: str
    ) -> None:
        """Test __init__."""
        obj = PersistentGraphLocked(message=message, reason=reason)
        assert obj.message == expected_msg


class TestPersistentGraphUnlocked:
    """Test PersistentGraphUnlocked."""

    @pytest.mark.parametrize(
        "message, reason, expected_msg",
        [
            (
                None,
                None,
                "Persistent graph is unlocked. This action requires the graph to "
                "be locked to be executed.",
            ),
            ("message", None, "message"),
            ("message", "reason", "message"),
            (None, "reason", "Persistent graph is unlocked. reason"),
        ],
    )
    def test___init__(
        self, message: Optional[str], reason: Optional[str], expected_msg: str
    ) -> None:
        """Test __init__."""
        obj = PersistentGraphUnlocked(message=message, reason=reason)
        assert obj.message == expected_msg
