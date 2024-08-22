"""Test classes."""

from __future__ import annotations

from typing import Any


class FakeTransferFutureCallArgs:
    """Fake TransferFutureCallArgs."""

    def __init__(self, *, extra_args: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Instantiate class."""
        self.extra_args = extra_args or {}
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)


class FakeTransferFutureMeta:
    """Fake TransferFutureMeta."""

    def __init__(
        self,
        size: int | None = None,
        call_args: FakeTransferFutureCallArgs | None = None,
        transfer_id: str | None = None,
    ) -> None:
        """Instantiate class."""
        self.size = size
        self.call_args = call_args or FakeTransferFutureCallArgs()
        self.transfer_id = transfer_id


class FakeTransferFuture:
    """Fake TransferFuture."""

    def __init__(
        self,
        result: str | None = None,
        exception: Exception | None = None,
        meta: FakeTransferFutureMeta = None,
    ) -> None:
        """Instantiate class."""
        self._result = result
        self._exception = exception
        self.meta = meta or FakeTransferFutureMeta()

    def result(self) -> str | None:
        """Return result."""
        if self._exception:
            raise self._exception
        return self._result
