"""Test classes."""

from __future__ import annotations

from typing import Any, Optional


class FakeTransferFutureCallArgs:
    """Fake TransferFutureCallArgs."""

    def __init__(self, *, extra_args: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Instantiate class."""
        self.extra_args = extra_args or {}
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)


class FakeTransferFutureMeta:
    """Fake TransferFutureMeta."""

    def __init__(
        self,
        size: Optional[int] = None,
        call_args: Optional[FakeTransferFutureCallArgs] = None,
        transfer_id: Optional[str] = None,
    ) -> None:
        """Instantiate class."""
        self.size = size
        self.call_args = call_args or FakeTransferFutureCallArgs()
        self.transfer_id = transfer_id


class FakeTransferFuture:
    """Fake TransferFuture."""

    def __init__(
        self,
        result: Optional[str] = None,
        exception: Optional[Exception] = None,
        meta: FakeTransferFutureMeta = None,
    ) -> None:
        """Instantiate class."""
        self._result = result
        self._exception = exception
        self.meta = meta or FakeTransferFutureMeta()

    def result(self) -> Optional[str]:
        """Return result."""
        if self._exception:
            raise self._exception
        return self._result
