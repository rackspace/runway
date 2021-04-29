"""CFNgin statuses."""
import operator
from typing import Any, Callable, Optional


class Status:
    """CFNgin status base class.

    Attributes:
        name: Name of the status.
        code: Status code.
        reason: Reason for the status.

    """

    code: int
    name: str
    reason: Optional[str]

    def __init__(self, name: str, code: int, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            name: Name of the status.
            code: Status code.
            reason: Reason for the status.

        """
        self.name = name
        self.code = code
        self.reason = reason or getattr(self, "reason", None)

    def _comparison(self, operator_: Callable[[Any, Any], bool], other: Any) -> bool:
        """Compare self to another object.

        Args:
            operator_: Operator for the comparison.
            other: The other object to compare to self.

        Raises:
            NotImplemented: other does not have ``code`` attribute.

        """
        if hasattr(other, "code"):
            return operator_(self.code, other.code)
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        """Compare if self is equal to another object."""
        return self._comparison(operator.eq, other)

    def __ne__(self, other: Any) -> bool:
        """Compare if self is not equal to another object."""
        return self._comparison(operator.ne, other)

    def __lt__(self, other: Any) -> bool:
        """Compare if self is less than another object."""
        return self._comparison(operator.lt, other)

    def __gt__(self, other: Any) -> bool:
        """Compare if self is greater than another object."""
        return self._comparison(operator.gt, other)

    def __le__(self, other: Any) -> bool:
        """Compare if self is less than or equal to another object."""
        return self._comparison(operator.le, other)

    def __ge__(self, other: Any) -> bool:
        """Compare if self is greater than equal to another object."""
        return self._comparison(operator.ge, other)


class CompleteStatus(Status):
    """Status name of 'complete' with code of '2'."""

    def __init__(self, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            reason: Reason for the status.

        """
        super().__init__("complete", 2, reason)


class FailedStatus(Status):
    """Status name of 'failed' with code of '4'."""

    def __init__(self, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            reason: Reason for the status.

        """
        super().__init__("failed", 4, reason)


class PendingStatus(Status):
    """Status name of 'pending' with code of '0'."""

    def __init__(self, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            reason: Reason for the status.

        """
        super().__init__("pending", 0, reason)


class SkippedStatus(Status):
    """Status name of 'skipped' with code of '3'."""

    def __init__(self, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            reason: Reason for the status.

        """
        super().__init__("skipped", 3, reason)


class SubmittedStatus(Status):
    """Status name of 'submitted' with code of '1'."""

    def __init__(self, reason: Optional[str] = None) -> None:
        """Instantiate class.

        Args:
            reason: Reason for the status.

        """
        super().__init__("submitted", 1, reason)


class DidNotChangeStatus(SkippedStatus):
    """Skipped status with a reason of 'nochange'."""

    reason = "nochange"


class DoesNotExistInCloudFormation(SkippedStatus):
    """Skipped status with a reason of 'does not exist in cloudformation'."""

    reason = "does not exist in cloudformation"


class NotSubmittedStatus(SkippedStatus):
    """Skipped status with a reason of 'disabled'."""

    reason = "disabled"


class NotUpdatedStatus(SkippedStatus):
    """Skipped status with a reason of 'locked'."""

    reason = "locked"


COMPLETE = CompleteStatus()
FAILED = FailedStatus()
INTERRUPTED = FailedStatus(reason="interrupted")
NO_CHANGE = DidNotChangeStatus()
PENDING = PendingStatus()
SKIPPED = SkippedStatus()
SUBMITTED = SubmittedStatus()
WAITING = PendingStatus(reason="waiting")
