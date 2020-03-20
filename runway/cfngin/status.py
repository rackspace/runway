"""CFNgin statuses."""
import operator


class Status(object):
    """CFNgin status base class.

    Attributes:
        name (str): Name of the status.
        code (int): Status code.
        reason (Optional[str]): Reason for the status.

    """

    def __init__(self, name, code, reason=None):
        """Instantiate class.

        Args:
            name (str): Name of the status.
            code (int): Status code.
            reason (Optional[str]): Reason for the status.

        """
        self.name = name
        self.code = code
        self.reason = reason or getattr(self, "reason", None)

    def _comparison(self, operator_, other):
        """Compare self to another object.

        Args:
            operator_ (operator): Operator for the comparison.
            other (Any): The other object to compare to self.

        Returns:
            bool: Whether the comparison passes.

        Raises:
            NotImplemented: other does not have ``code`` attribute.

        """
        if hasattr(other, "code"):
            return operator_(self.code, other.code)
        return NotImplemented

    def __eq__(self, other):
        """Compare if self is equal to another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.eq, other)

    def __ne__(self, other):
        """Compare if self is not equal to another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.ne, other)

    def __lt__(self, other):
        """Compare if self is less than another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.lt, other)

    def __gt__(self, other):
        """Compare if self is greater than another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.gt, other)

    def __le__(self, other):
        """Compare if self is less than or equal to another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.le, other)

    def __ge__(self, other):
        """Compare if self is greater than equal to another object.

        Returns:
            bool: Whether the comparison passes.

        """
        return self._comparison(operator.ge, other)


class CompleteStatus(Status):  # pylint: disable=too-few-public-methods
    """Status name of 'complete' with code of '2'."""

    def __init__(self, reason=None):
        """Instantiate class.

        Args:
            reason (Optional[str]): Reason for the status.

        """
        super(CompleteStatus, self).__init__("complete", 2, reason)


class FailedStatus(Status):  # pylint: disable=too-few-public-methods
    """Status name of 'failed' with code of '4'."""

    def __init__(self, reason=None):
        """Instantiate class.

        Args:
            reason (Optional[str]): Reason for the status.

        """
        super(FailedStatus, self).__init__("failed", 4, reason)


class PendingStatus(Status):  # pylint: disable=too-few-public-methods
    """Status name of 'pending' with code of '0'."""

    def __init__(self, reason=None):
        """Instantiate class.

        Args:
            reason (Optional[str]): Reason for the status.

        """
        super(PendingStatus, self).__init__("pending", 0, reason)


class SkippedStatus(Status):  # pylint: disable=too-few-public-methods
    """Status name of 'skipped' with code of '3'."""

    def __init__(self, reason=None):
        """Instantiate class.

        Args:
            reason (Optional[str]): Reason for the status.

        """
        super(SkippedStatus, self).__init__("skipped", 3, reason)


class SubmittedStatus(Status):  # pylint: disable=too-few-public-methods
    """Status name of 'submitted' with code of '1'."""

    def __init__(self, reason=None):
        """Instantiate class.

        Args:
            reason (Optional[str]): Reason for the status.

        """
        super(SubmittedStatus, self).__init__("submitted", 1, reason)


class DidNotChangeStatus(SkippedStatus):  # pylint: disable=too-few-public-methods
    """Skipped status with a reason of 'nochange'."""

    reason = "nochange"


class NotSubmittedStatus(SkippedStatus):  # pylint: disable=too-few-public-methods
    """Skipped status with a reason of 'disabled'."""

    reason = "disabled"


class NotUpdatedStatus(SkippedStatus):  # pylint: disable=too-few-public-methods
    """Skipped status with a reason of 'locked'."""

    reason = "locked"


class StackDoesNotExist(SkippedStatus):  # pylint: disable=too-few-public-methods
    """Skipped status with a reason of 'does not exist in cloudformation'."""

    reason = "does not exist in cloudformation"


COMPLETE = CompleteStatus()
FAILED = FailedStatus()
INTERRUPTED = FailedStatus(reason="interrupted")
NO_CHANGE = DidNotChangeStatus()
PENDING = PendingStatus()
SKIPPED = SkippedStatus()
SUBMITTED = SubmittedStatus()
WAITING = PendingStatus(reason="waiting")
