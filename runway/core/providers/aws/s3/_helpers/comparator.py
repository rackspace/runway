"""Comparator.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/comparator.py

"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generator, Iterator, cast

if TYPE_CHECKING:
    from .file_info import FileInfo
    from .sync_strategy.base import BaseSync


LOGGER = logging.getLogger(__name__)


class Comparator:
    """Performs all of the comparisons behind the sync operation."""

    def __init__(
        self,
        file_at_src_and_dest_sync_strategy: BaseSync,
        file_not_at_dest_sync_strategy: BaseSync,
        file_not_at_src_sync_strategy: BaseSync,
    ):
        """Instantiate class."""
        self._sync_strategy = file_at_src_and_dest_sync_strategy
        self._not_at_dest_sync_strategy = file_not_at_dest_sync_strategy
        self._not_at_src_sync_strategy = file_not_at_src_sync_strategy

    def call(
        self, src_files: Iterator[FileInfo], dest_files: Iterator[FileInfo]
    ) -> Generator[FileInfo, None, None]:
        """Preform the actual comparisons.

        The parameters this takes are the generated files for both the source
        and the destination. The key concept in this function is that no matter
        the type of where the files are coming from, they are listed in the same
        order, least to greatest in collation order. This allows for easy
        comparisons to determine if file needs to be added or deleted. Comparison
        keys are used to determine if two files are the same and each file has a
        unique comparison key. If they are the same compare the size and last
        modified times to see if a file needs to be updated. Ultimately, it will
        yield a sequence of file info objects that will be sent to the
        ``S3Handler``.

        Algorithm:
            Try to take next from both files. If it is empty signal
            corresponding done flag. If both generated lists are not done
            compare compare_keys. If equal, compare size and time to see if
            it needs to be updated. If source compare_key is less than dest
            compare_key, the file needs to be added to the destination. Take
            the next source file but not not destination file. If the source
            compare_key is greater than dest compare_key, that destination file
            needs to be deleted from the destination. Take the next dest file
            but not the source file. If the source list is empty delete the
            rest of the files in the dest list from the destination. If the
            dest list is empty add the rest of the file in source list to
            the destination.

        Args:
            src_files: The generated FileInfo objects from the source.
            dest_files: The generated FileInfo objects from the dest.

        Returns:
            Yields the FilInfo objects of the files that need to be operated on.

        """
        src_done = False  # True if there are no more files from the source left.
        dest_done = False  # True if there are no more files form the dest left.
        src_take = True  # Take the next source file from the generated files if true
        dest_take = True  # Take the next dest file from the generated files if true
        while True:
            try:
                if not src_done and src_take:
                    src_file = next(src_files)
            except StopIteration:
                src_file = None
                src_done = True

            try:
                if not dest_done and dest_take:
                    dest_file = next(dest_files)
            except StopIteration:
                dest_file = None
                dest_done = True

            if not src_done and not dest_done:
                src_take = True
                dest_take = True

                compare_keys = self.compare_comp_key(src_file, dest_file)  # type: ignore

                if compare_keys == "equal":
                    should_sync = self._sync_strategy.determine_should_sync(
                        src_file, dest_file  # type: ignore
                    )
                    if should_sync:
                        yield src_file  # type: ignore
                elif compare_keys == "less_than":
                    src_take = True
                    dest_take = False
                    should_sync = self._not_at_dest_sync_strategy.determine_should_sync(
                        src_file, None  # type: ignore
                    )
                    if should_sync:
                        yield src_file  # type: ignore

                elif compare_keys == "greater_than":
                    src_take = False
                    dest_take = True
                    should_sync = self._not_at_src_sync_strategy.determine_should_sync(
                        None, dest_file  # type: ignore
                    )
                    if should_sync:
                        yield dest_file  # type: ignore

            elif (not src_done) and dest_done:
                src_take = True
                should_sync = self._not_at_dest_sync_strategy.determine_should_sync(
                    src_file, None  # type: ignore
                )
                if should_sync:
                    yield src_file  # type: ignore

            elif src_done and (not dest_done):
                dest_take = True
                should_sync = self._not_at_src_sync_strategy.determine_should_sync(
                    None, dest_file  # type: ignore
                )
                if should_sync:
                    yield dest_file  # type: ignore
            else:
                break

    @staticmethod
    def compare_comp_key(src_file: FileInfo, dest_file: FileInfo) -> str:
        """Compare the source & destination compare_key."""
        src_comp_key = cast(str, src_file.compare_key)
        dest_comp_key = cast(str, dest_file.compare_key)
        if src_comp_key == dest_comp_key:
            return "equal"
        if src_comp_key < dest_comp_key:
            return "less_than"
        return "greater_than"
