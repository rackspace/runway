"""Register sync strategies.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/register.py

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type

from .delete import DeleteSync
from .exact_timestamps import ExactTimestampsSync
from .size_only import SizeOnlySync

if TYPE_CHECKING:
    from botocore.session import Session

    from .base import BaseSync, ValidSyncType


def register_sync_strategy(
    session: Session,
    strategy_cls: Type[BaseSync],
    sync_type: ValidSyncType = "file_at_src_and_dest",
):
    """Register a single sync strategy.

    Args:
        session: The session that the sync strategy is being registered to.
        strategy_cls: The class of the sync strategy to be registered.
        sync_type: A string representing when to perform the sync strategy.
            See ``__init__`` method of ``BaseSyncStrategy`` for possible options.

    """
    strategy = strategy_cls(sync_type)
    strategy.register_strategy(session)


def register_sync_strategies(session: Session, **_: Any) -> None:
    """Register the different sync strategies."""
    # Register the size only sync strategy.
    register_sync_strategy(session, SizeOnlySync)

    # Register the exact timestamps sync strategy.
    register_sync_strategy(session, ExactTimestampsSync)

    # Register the delete sync strategy.
    register_sync_strategy(session, DeleteSync, "file_not_at_src")
