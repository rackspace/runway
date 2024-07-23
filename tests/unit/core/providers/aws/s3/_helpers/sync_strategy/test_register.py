"""Test runway.core.providers.aws.s3._helpers.sync_strategy.register."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, call

from runway.core.providers.aws.s3._helpers.sync_strategy import (
    DeleteSync,
    ExactTimestampsSync,
    SizeOnlySync,
)
from runway.core.providers.aws.s3._helpers.sync_strategy.register import (
    register_sync_strategies,
    register_sync_strategy,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.core.providers.aws.s3._helpers.sync_strategy.register"


def test_register_sync_strategies(mocker: MockerFixture) -> None:
    """Test register_sync_strategies."""
    mock_register = mocker.patch(f"{MODULE}.register_sync_strategy", Mock())
    session = Mock()
    assert not register_sync_strategies(session)
    mock_register.assert_has_calls(
        [
            call(session, SizeOnlySync),
            call(session, ExactTimestampsSync),
            call(session, DeleteSync, "file_not_at_src"),
        ],
        any_order=False,
    )


def test_register_sync_strategy() -> None:
    """Test register_sync_strategy."""
    session = Mock()
    strategy_object = Mock()
    strategy_cls = Mock(return_value=strategy_object)
    assert not register_sync_strategy(session, strategy_cls, "sync_type")  # type: ignore
    strategy_cls.assert_called_once_with("sync_type")
    strategy_object.register_strategy.assert_called_once_with(session)


def test_register_sync_strategy_default() -> None:
    """Test register_sync_strategy."""
    strategy_cls = Mock()
    assert not register_sync_strategy(Mock(), strategy_cls)  # type: ignore
    strategy_cls.assert_called_once_with("file_at_src_and_dest")
