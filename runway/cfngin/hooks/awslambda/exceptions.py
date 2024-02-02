"""Exceptions for awslambda hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...exceptions import CfnginError

if TYPE_CHECKING:
    from pathlib import Path


class DeploymentPackageEmptyError(CfnginError):
    """Deployment package is empty.

    This can be caused by an incorrect source code directory or a gitignore rule
    unintentionally ignoring all source code.

    Any empty deployment package is determined by checking the size of the
    archive file. If the size is <=22 (the size a zip file End of Central
    Directory Record) it has no contents.

    """

    archive_file: Path
    """The deployment package archive file."""

    def __init__(self, archive_file: Path) -> None:
        """Instantiate class.

        Args:
            archive_file: The empty archive file.

        """
        self.archive_file = archive_file
        self.message = f"{archive_file.name} contains no files"
        super().__init__()


class RuntimeMismatchError(CfnginError):
    """Required runtime does not match the detected runtime."""

    detected_runtime: str
    """Runtime detected on the build system."""

    expected_runtime: str
    """Explicitly defined runtime that was expected."""

    def __init__(self, expected_runtime: str, detected_runtime: str) -> None:
        """Instantiate class.

        Args:
            expected_runtime: Explicitly defined runtime that was expected.
            detected_runtime: Runtime detected on the build system.

        """
        self.detected_runtime = detected_runtime
        self.expected_runtime = expected_runtime
        self.message = (
            f"{detected_runtime} runtime determined from the build system"
            f" does not match the expected {expected_runtime} runtime"
        )
        super().__init__()
